"""
T2: Session管理API路由
"""
import uuid
from datetime import datetime
from fastapi import APIRouter
from backend.db.connection import get_poi_conn, get_user_conn, dict_from_row
from backend.db.models import CreateSessionRequest

router = APIRouter()


@router.post("/session")
def create_session(req: CreateSessionRequest):
    """创建新会话"""
    # 查找城市
    poi_conn = get_poi_conn()
    cur = poi_conn.cursor()
    cur.execute("SELECT * FROM city WHERE name LIKE ?", (f"%{req.city_name}%",))
    city = dict_from_row(cur.fetchone())
    if not city:
        return {"ok": False, "error": f"城市 '{req.city_name}' 不在库中"}

    # 创建session
    session_id = str(uuid.uuid4())[:8]
    user_conn = get_user_conn()
    ucur = user_conn.cursor()
    ucur.execute("""
        INSERT INTO session (session_id, user_id, city_name, city_id, days, current_phase)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, f"user_{session_id}", req.city_name, city["city_id"], req.days, "card_flow"))
    user_conn.commit()

    # 插入默认偏好
    ucur.execute("""
        INSERT INTO user_preference (session_id)
        VALUES (?)
    """, (session_id,))
    user_conn.commit()

    return {
        "ok": True,
        "data": {
            "session_id": session_id,
            "phase": "card_flow",
            "city": city,
            "days": req.days,
        }
    }


@router.get("/session/{session_id}")
def get_session(session_id: str):
    """获取会话状态"""
    user_conn = get_user_conn()
    cur = user_conn.cursor()
    cur.execute("SELECT * FROM session WHERE session_id=?", (session_id,))
    session = dict_from_row(cur.fetchone())
    if not session:
        return {"ok": False, "error": "Session不存在"}
    return {"ok": True, "data": session}


@router.get("/profile/{session_id}")
def get_profile(session_id: str):
    """获取当前约束快照"""
    user_conn = get_user_conn()
    cur = user_conn.cursor()
    cur.execute("SELECT * FROM user_preference WHERE session_id=?", (session_id,))
    pref = dict_from_row(cur.fetchone())
    if not pref:
        return {"ok": False, "error": "该session无偏好数据"}
    return {"ok": True, "data": pref}


@router.post("/profile/{session_id}")
def update_profile(session_id: str, req: dict):
    """更新约束（支持部分更新）"""
    allowed_fields = {
        "num_people", "arrival_time", "departure_time", "accommodation",
        "transport_mode", "pace", "food_preference", "budget_per_day",
        "special_requirements",
    }
    updates = {k: v for k, v in req.items() if k in allowed_fields and v is not None}
    if not updates:
        return {"ok": False, "error": "无有效字段"}

    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [session_id]

    user_conn = get_user_conn()
    cur = user_conn.cursor()
    cur.execute(f"UPDATE user_preference SET {set_clause} WHERE session_id=?", values)
    user_conn.commit()

    # 更新session时间
    cur.execute("UPDATE session SET updated_at=datetime('now','localtime') WHERE session_id=?", (session_id,))
    user_conn.commit()

    return {"ok": True, "data": {"updated": list(updates.keys())}}

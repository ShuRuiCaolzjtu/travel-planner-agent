"""
T5: 约束收集 API 路由
"""
from fastapi import APIRouter, HTTPException
from backend.db.connection import get_user_conn
from backend.agent.constraint_agent import ConstraintAgent, CONSTRAINT_FIELDS

router = APIRouter()

_agents: dict[str, ConstraintAgent] = {}


@router.get("/constraint/start/{session_id}")
def start_constraint(session_id: str):
    uconn = get_user_conn()
    ucur = uconn.cursor()
    ucur.execute("SELECT days FROM session WHERE session_id=?", (session_id,))
    row = ucur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session不存在")

    days = row[0]
    ucur.execute("SELECT COUNT(*) FROM poi_score WHERE session_id=?", (session_id,))
    scored_count = ucur.fetchone()[0]

    agent = ConstraintAgent(session_id, days=days, scored_count=scored_count)

    ucur.execute("SELECT * FROM user_preference WHERE session_id=?", (session_id,))
    pref = ucur.fetchone()
    if pref:
        field_names = ["num_people", "arrival_time", "departure_time", "accommodation",
                       "transport_mode", "pace", "food_preference", "budget_per_day",
                       "special_requirements"]
        for i, fn in enumerate(field_names):
            val = pref[i + 2]
            if val is not None:
                agent.constraints[fn] = val
                agent.collected_fields.add(fn)

    _agents[session_id] = agent
    question = agent.get_next_question()
    return {"ok": True, "data": {"question": question, "finished": False}}


@router.post("/constraint/chat/{session_id}")
def constraint_chat(session_id: str, body: dict):
    message = body.get("message", "")
    if not message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    agent = _agents.get(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="请先调用 /constraint/start")

    response = None
    try:
        response = agent.process_message(message)
    except Exception:
        pass

    if response is None:
        try:
            response = agent._process_with_rules(message)
            response["llm_fallback"] = True
        except Exception:
            idx = agent._current_field_index()
            q = CONSTRAINT_FIELDS[idx][2] if idx < 8 else "都记下了！"
            return {
                "ok": True,
                "data": {"question": q, "finished": False, "conflicts": [], "llm_fallback": True}
            }

    # 保存约束到数据库
    try:
        uconn = get_user_conn()
        ucur = uconn.cursor()
        up = {}
        # 字段名→DB列名映射（agent用arrival_info，DB用arrival_time）
        db_field_map = {"arrival_info": "arrival_time", "departure_info": "departure_time"}
        for k, v in agent.constraints.items():
            dbk = db_field_map.get(k, k)  # 映射到DB列名
            if dbk in ("accommodation_lat", "accommodation_lon"):
                up[dbk] = v
            elif dbk in ("num_people", "budget_per_day"):
                try:
                    up[dbk] = int(float(v)) if v else None
                except Exception:
                    up[dbk] = None
            else:
                up[dbk] = str(v) if v else None
        if up:
            cols = ", ".join(f"{k}=?" for k in up)
            ucur.execute(f"UPDATE user_preference SET {cols} WHERE session_id=?", list(up.values()) + [session_id])
            uconn.commit()
    except Exception as _e:
        print(f"[constraint] 保存失败: {_e}")

    # 日志：当前状态
    print(f"[约束状态] 已收集={sorted(agent.collected_fields)} 值={agent.constraints}")

    if response.get("is_complete"):
        try:
            uconn = get_user_conn()
            ucur = uconn.cursor()
            ucur.execute("UPDATE session SET current_phase='planning' WHERE session_id=?", (session_id,))
            uconn.commit()
        except Exception:
            pass

    return {
        "ok": True,
        "data": {
            "question": response.get("next_question", ""),
            "finished": response.get("is_complete", False),
            "conflicts": response.get("conflicts", []),
            "llm_fallback": response.get("llm_fallback", False),
        }
    }


@router.get("/constraint/status/{session_id}")
def constraint_status(session_id: str):
    agent = _agents.get(session_id)
    if not agent:
        return {"ok": True, "data": {"started": False}}
    return {
        "ok": True,
        "data": {
            "started": True,
            "finished": agent.finished,
            "collected": list(agent.collected_fields),
            "total": 8,
            "constraints": agent.constraints,
        }
    }

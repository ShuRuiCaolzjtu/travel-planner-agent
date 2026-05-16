"""
T2: POI相关API路由
"""
import json
from fastapi import APIRouter, HTTPException, Query
from backend.db.connection import get_poi_conn, dict_from_row
from backend.db.models import ScoreRequest

router = APIRouter()


EXCLUDE_NAMES = [
    # 住宿类
    '酒店', '宾馆', '公寓', '民宿', '客栈', '旅舍', '招待所',
    '度假', '别墅', '美墅', '美宿', '旅居', '商旅', '艺墅',
    '尚居', '华府', '河畔', '青城', '瑞城', '满江印', '云想山',
    # 非旅游商业
    '国际', '足浴', '公厕', '停车场', '超市', '便利店', '通信',
    '公司', '集团', '办事处', '门诊', '医院', '诊所',
    '花园', '新城', '花苑', '农贸市场', '菜市场',
    '购物公园', '泰业', '昆百大',
    # 非景点类被误标记的
    '专卖店', '授权店',
    # 连锁店/快递
    '7-ELEVEn', '屈臣氏', '名创优品', 'MINISO', '京东快递',
    '九机', '手机', '电脑数码',
]

def _is_tourist_poi(row) -> bool:
    """判断POI是否对游客有参考价值"""
    name = row[2]  # poi.name
    for kw in EXCLUDE_NAMES:
        if kw in name:
            return False
    return True


@router.get("/poi/cards")
def get_poi_cards(session_id: str = Query(...), count: int = Query(default=3, ge=1, le=10)):
    """获取下一批POI卡片（排除已评分的和非旅游类POI）"""
    from backend.db.connection import get_user_conn
    conn = get_poi_conn()
    cur = conn.cursor()

    # 获取session信息（user.db中的session表）
    uconn = get_user_conn()
    ucur = uconn.cursor()
    ucur.execute("SELECT city_id, city_name FROM session WHERE session_id=?", (session_id,))
    session_row = ucur.fetchone()
    if not session_row:
        raise HTTPException(status_code=404, detail="Session不存在或已过期")
    city_id = session_row[0]

    # 获取该session已评分的POI
    ucur.execute("SELECT poi_id FROM poi_score WHERE session_id=?", (session_id,))
    scored_ids = {row[0] for row in ucur.fetchall()}

    # 从LLM过滤后的POI中取候选，优先展示景点，再美食/活动
    FETCH_SIZE = 200
    cur.execute("""
        SELECT * FROM poi
        WHERE city_id = ? AND status = 'active' AND llm_status = 'active'
        ORDER BY
            CASE type WHEN '景点' THEN 0 WHEN '活动' THEN 1 WHEN '美食' THEN 2 WHEN '购物' THEN 3 ELSE 4 END,
            rating DESC, rating_count DESC
        LIMIT ?
    """, (city_id, FETCH_SIZE))
    all_candidates = cur.fetchall()

    cards = []
    for row in all_candidates:
        if row[0] in scored_ids:
            continue
        cards.append(row)
        if len(cards) >= count:
            break

    # 格式化
    result = []
    for c in cards:
        try:
            tags = json.loads(c[12]) if isinstance(c[12], str) else (c[12] or [])
        except (json.JSONDecodeError, TypeError):
            tags = []
        result.append({
            "poi_id": c[0],
            "name": c[2],
            "type": c[3],
            "lat": c[4],
            "lon": c[5],
            "duration_min": c[6],
            "open_time": c[7],
            "close_time": c[8],
            "avg_cost": c[9],
            "rating": c[10],
            "rating_count": c[11],
            "tags": tags,
            "summary": c[25] or c[13] or "",  # llm_summary优先，后补原始摘要
            "district": c[18],
        })

    return {"ok": True, "data": {"cards": result, "remaining": max(0, 50 - len(scored_ids))}}


@router.post("/poi/{poi_id}/score")
def score_poi(poi_id: str, req: ScoreRequest):
    """保存POI评分"""
    conn = get_poi_conn()
    from backend.db.connection import get_user_conn
    uconn = get_user_conn()
    cur = uconn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO poi_score (session_id, poi_id, score, gesture)
        VALUES (?, ?, ?, ?)
    """, (req.session_id, poi_id, req.score, req.gesture))
    uconn.commit()
    return {"ok": True, "data": {"poi_id": poi_id, "score": req.score}}


@router.get("/poi/{poi_id}")
def get_poi_detail(poi_id: str):
    """获取POI详情"""
    conn = get_poi_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM poi WHERE poi_id=?", (poi_id,))
    poi = dict_from_row(cur.fetchone())
    if not poi:
        raise HTTPException(status_code=404, detail="POI不存在")
    try:
        poi["tags"] = json.loads(poi["tags"]) if isinstance(poi["tags"], str) else poi["tags"]
    except (json.JSONDecodeError, TypeError):
        poi["tags"] = []
    try:
        poi["gallery"] = json.loads(poi["gallery"]) if isinstance(poi["gallery"], str) else poi["gallery"]
    except (json.JSONDecodeError, TypeError):
        poi["gallery"] = []
    return {"ok": True, "data": poi}

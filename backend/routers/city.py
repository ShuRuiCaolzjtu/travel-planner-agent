"""
T2: 城市API路由
"""
from fastapi import APIRouter, HTTPException
from backend.db.connection import get_poi_conn, dict_from_row

router = APIRouter()


@router.get("/city/{city_name}")
def get_city(city_name: str):
    conn = get_poi_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM city WHERE name LIKE ?", (f"%{city_name}%",))
    city = dict_from_row(cur.fetchone())
    if not city:
        # 尝试别名匹配
        alias_map = {"大理": "大理", "dali": "大理", "丽江": None, "昆明": None}
        target = alias_map.get(city_name)
        if target:
            cur.execute("SELECT * FROM city WHERE name = ?", (target,))
            city = dict_from_row(cur.fetchone())
    if not city:
        raise HTTPException(status_code=404, detail=f"城市 '{city_name}' 不在库中")
    return {"ok": True, "data": city}

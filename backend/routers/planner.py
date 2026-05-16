"""
T3: 规划引擎 API 路由
"""
import json
from fastapi import APIRouter, HTTPException
from backend.db.connection import get_poi_conn, get_user_conn, get_dist_conn, dict_from_row
from backend.db.models import RunPlannerRequest, AdjustPlannerRequest
from backend.planner.solver import run_planner
from backend.planner.adjust import incremental_adjust

router = APIRouter()


@router.post("/planner/run")
def planner_run(req: RunPlannerRequest):
    """运行规划引擎"""
    uconn = get_user_conn()
    ucur = uconn.cursor()

    # 获取session信息
    ucur.execute("SELECT * FROM session WHERE session_id=?", (req.session_id,))
    session = dict_from_row(ucur.fetchone())
    if not session:
        raise HTTPException(status_code=404, detail="Session不存在")

    city_id = session["city_id"]
    days = session.get("days", 3)

    # 获取用户偏好
    ucur.execute("SELECT * FROM user_preference WHERE session_id=?", (req.session_id,))
    pref = dict_from_row(ucur.fetchone()) or {}

    # 获取已评分的POI（含分数）
    ucur.execute("SELECT poi_id, score FROM poi_score WHERE session_id=?", (req.session_id,))
    scored_rows = ucur.fetchall()
    scored_ids = [r[0] for r in scored_rows]
    poi_scores = {r[0]: r[1] for r in scored_rows}

    # 获取POI数据（只取评分最高的80个，保证规划速度）
    conn = get_poi_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM poi
        WHERE city_id = ? AND status = 'active' AND llm_status = 'active'
        ORDER BY rating DESC
        LIMIT 80
    """, (city_id,))
    all_pois_data = cur.fetchall()

    # 转为dict列表
    pois = []
    for p in all_pois_data:
        try:
            tags = json.loads(p[12]) if isinstance(p[12], str) else []
        except (json.JSONDecodeError, TypeError):
            tags = []
        pois.append({
            "poi_id": p[0],
            "name": p[2],
            "type": p[3],
            "lat": p[4],
            "lon": p[5],
            "duration_min": p[6],
            "open_time": p[7],
            "close_time": p[8],
            "avg_cost": p[9],
            "rating": p[10],
            "tags": tags,
        })

    # 调用规划引擎
    import time as _timer
    _t0 = _timer.time()
    pace = pref.get("pace", "standard")
    accommodation = pref.get("accommodation", "古城")
    budget = pref.get("budget_per_day")
    # 从LLM提取的结构化值中解析时间+地点
    # 格式: "7:00@大理站" 或 "21:00@大理站" 或 "7:00"（仅时间）
    import re as _re
    arrival_time = None; departure_time = None
    arrival_loc = None; departure_loc = None
    station_coord = None

    for raw, out_time, out_loc in [
        (pref.get("arrival_time") or pref.get("arrival_info", "") or "", "arrival_time", "arrival_loc"),
        (pref.get("departure_time") or pref.get("departure_info", "") or "", "departure_time", "departure_loc"),
    ]:
        loc_name = ""
        time_str = raw

        # 尝试结构化格式 "7:00@大理站"
        if "@" in raw:
            parts = raw.split("@", 1)
            time_str = parts[0].strip()
            loc_name = parts[1].strip()
        else:
            # 兜底：从原始文本中提取站名
            m = _re.search(r'(\S*?站)', raw)
            if m:
                loc_name = m.group(1)

        if out_time == "arrival_time": arrival_time = time_str
        else: departure_time = time_str
        if out_loc == "arrival_loc": arrival_loc = loc_name
        else: departure_loc = loc_name

        if loc_name:
            try:
                import requests as _r2
                r = _r2.get("https://restapi.amap.com/v3/geocode/geo",
                            params={"key":"d7eb03b1cbcdc5673d74eb0d7ebe6eba","address":loc_name+",大理","city":"大理"},
                            timeout=3)
                g = r.json()
                if g.get("geocodes") and g["geocodes"][0].get("location"):
                    loc = g["geocodes"][0]["location"].split(",")
                    station_coord = (float(loc[1]), float(loc[0]))
            except Exception:
                pass
            if station_coord is None:
                station_coord = (25.5917, 100.2733)

    hotel_coord = None
    AREA_COORDS = {"古城": (25.6814, 100.1647), "双廊": (25.9527, 100.1276),
                   "喜洲": (25.8543, 100.0120), "海东": (25.5970, 100.2805),
                   "才村": (25.6650, 100.1820), "苍山": (25.6667, 100.1000),
                   "市中心": (25.6065, 100.2299)}
    KNOWN = tuple(AREA_COORDS.keys())
    if accommodation and accommodation not in KNOWN:
        try:
            import requests as _r3
            # 1. POI搜索（在线查高德，完整名称）
            r = _r3.get("https://restapi.amap.com/v3/place/text",
                        params={"key":"d7eb03b1cbcdc5673d74eb0d7ebe6eba",
                                "keywords":accommodation,"city":"大理","offset":3},
                        timeout=3)
            p = r.json()
            if p.get("count") and int(p["count"]) > 0 and p.get("pois"):
                loc = p["pois"][0]["location"].split(",")
                hotel_coord = (float(loc[1]), float(loc[0]))
                print(f"[planner] POI搜索: {accommodation} → {p['pois'][0]['name']} {hotel_coord}")
        except Exception as e:
            print(f"[planner] 高德查询异常: {e}")

        if hotel_coord is None:
            try:
                # 2. 地理编码兜底
                r3 = _r3.get("https://restapi.amap.com/v3/geocode/geo",
                            params={"key":"d7eb03b1cbcdc5673d74eb0d7ebe6eba",
                                    "address":accommodation,"city":"大理"},
                            timeout=3)
                g = r3.json()
                if g.get("geocodes") and g["geocodes"][0].get("location"):
                    loc = g["geocodes"][0]["location"].split(",")
                    hotel_coord = (float(loc[1]), float(loc[0]))
                    print(f"[planner] 地理编码兜底: {accommodation} → {hotel_coord}")
            except Exception:
                pass

        if hotel_coord is None:
            # 全没查到，从酒店名推断区域
            AREA_KEYWORDS = {"古城":"古城","大理古城":"古城","双廊":"双廊","喜洲":"喜洲",
                             "海东":"海东","才村":"才村","苍山":"苍山",
                             "洱海":"古城","市区":"市中心","下关":"市中心"}
            for kw, area in AREA_KEYWORDS.items():
                if kw in accommodation:
                    hotel_coord = AREA_COORDS.get(area)
                    print(f"[planner] 推断区域: {accommodation} → {area}")
                    break
                    print(f"[planner] 从酒店名推断区域: {accommodation} → {area}")
                    break

    result = run_planner(
        pois=pois, days=days, pace=pace,
        accommodation=accommodation,
        scored_ids=scored_ids, poi_scores=poi_scores,
        budget_per_day=budget,
        arrival_time=arrival_time,
        departure_time=departure_time,
        station_coord=station_coord, hotel_coord=hotel_coord,
        arrival_location=arrival_loc, departure_location=departure_loc,
    )

    # 打印耗时日志
    _t1 = _timer.time()
    print(f"[planner] 总耗时: {_t1-_t0:.2f}s, 其中规划引擎: {result['elapsed_ms']}ms, POI数: {len(pois)}")

    # 保存规划结果
    ucur.execute("""
        INSERT INTO planning_result (session_id, route_json, excluded_json, elapsed_ms)
        VALUES (?, ?, ?, ?)
    """, (
        req.session_id,
        json.dumps(result["routes"], ensure_ascii=False),
        json.dumps(result["excluded"], ensure_ascii=False),
        result["elapsed_ms"],
    ))
    uconn.commit()

    # 更新session阶段
    ucur.execute("UPDATE session SET current_phase='result', updated_at=datetime('now','localtime') WHERE session_id=?",
                 (req.session_id,))
    uconn.commit()

    return {
        "ok": True,
        "data": {
            "routes": result["routes"],
            "excluded": result["excluded"],
            "elapsed_ms": result["elapsed_ms"],
        }
    }


@router.post("/planner/adjust")
def planner_adjust(req: AdjustPlannerRequest):
    """调整行程"""
    uconn = get_user_conn()
    ucur = uconn.cursor()

    # 获取当前规划结果
    ucur.execute("""
        SELECT route_json, excluded_json FROM planning_result
        WHERE session_id=? ORDER BY created_at DESC LIMIT 1
    """, (req.session_id,))
    row = ucur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="未找到规划结果，请先运行规划")

    current_routes = json.loads(row[0]) if isinstance(row[0], str) else row[0]

    # 获取POI数据（用于新增操作）
    conn = get_poi_conn()
    cur = conn.cursor()
    # session在user.db，先获取city_id
    ucur.execute("SELECT city_id FROM session WHERE session_id=?", (req.session_id,))
    session_row = ucur.fetchone()
    city_id = session_row[0] if session_row else ""
    cur.execute("SELECT * FROM poi WHERE city_id=?",
                (city_id,))
    all_pois_data = cur.fetchall()
    all_pois = []
    for p in all_pois_data:
        all_pois.append({
            "poi_id": p[0],
            "name": p[2],
            "type": p[3],
            "lat": p[4],
            "lon": p[5],
            "duration_min": p[6],
            "avg_cost": p[9],
            "rating": p[10],
        })

    if req.action == "change_pace" and req.pace:
        # 切换节奏 → 全量重规划
        ucur.execute("UPDATE user_preference SET pace=? WHERE session_id=?", (req.pace, req.session_id))
        uconn.commit()
        # 重新调用规划引擎
        new_req = RunPlannerRequest(session_id=req.session_id)
        return planner_run(new_req)

    elif req.action == "replan":
        # 一键重规划
        return planner_run(RunPlannerRequest(session_id=req.session_id))

    else:
        # add / remove → 增量调整
        new_routes = incremental_adjust(current_routes, req.action, req.poi_id, all_pois=all_pois)
        return {
            "ok": True,
            "data": {
                "routes": new_routes,
                "changes": [f"{req.action} 操作完成"],
            }
        }


@router.get("/planner/result/{session_id}")
def get_planner_result(session_id: str):
    """获取已生成的行程"""
    uconn = get_user_conn()
    ucur = uconn.cursor()
    ucur.execute("""
        SELECT route_json, excluded_json, elapsed_ms FROM planning_result
        WHERE session_id=? ORDER BY created_at DESC LIMIT 1
    """, (session_id,))
    row = ucur.fetchone()
    if not row:
        return {"ok": False, "error": "尚未运行规划"}
    try:
        routes = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        excluded = json.loads(row[1]) if isinstance(row[1], str) else row[1]
    except (json.JSONDecodeError, TypeError):
        routes = row[0]
        excluded = row[1]
    return {
        "ok": True,
        "data": {
            "routes": routes,
            "excluded": excluded,
            "elapsed_ms": row[2],
        }
    }

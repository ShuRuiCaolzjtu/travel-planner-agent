"""
路径规划引擎 v6 — 完全动态：根据LLM提取的约束自动组装路线
"""
import random, time, re
from backend.planner.distance import DistanceCache
from backend.planner.constraints import get_day_capacity, minutes_to_time
from backend.planner.adjust import build_route_for_day

# 默认住宿坐标（片区名→坐标）
DEFAULT_ACCOMMODATION = {
    "古城": (25.6814, 100.1647), "双廊": (25.9527, 100.1276),
    "喜洲": (25.8543, 100.0120), "海东": (25.5970, 100.2805),
    "才村": (25.6650, 100.1820), "苍山": (25.6667, 100.1000),
    "市中心": (25.6065, 100.2299),
}


_CN_NUM = {'零':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,
           '两':2,'十':10,'十一':11,'十二':12,'十三':13,'十四':14,'十五':15,'十六':16,
           '十七':17,'十八':18,'十九':19,'二十':20,'二十一':21,'二十二':22,'二十三':23}

def _parse_time(text: str) -> int | None:
    if not text: return None
    # 支持"七点"、"九点"、"十二点"等中文数字
    m = re.search(r'([0-9一二三四五六七八九十两]+)[：:点时](\d{0,2})', text)
    if m:
        h_str = m.group(1)
        h = _CN_NUM.get(h_str, int(h_str) if h_str.isdigit() else -1)
        mi = int(m.group(2) or 0)
        if '下午' in text and h < 12: h += 12
        if '中午' in text and h < 12: h = 12
        if '晚上' in text and h <= 6: h += 12  # "晚上九点" = 21:00
        if 0 <= h <= 23 and 0 <= mi <= 59: return h * 60 + mi
    return None


def travel_between(a, b, dc) -> int:
    return max(5, dc.estimate(a[0], a[1], b[0], b[1]))


def run_planner(pois, days=3, pace="relaxed", accommodation="古城",
                scored_ids=None, excluded_poi_ids=None, poi_scores=None,
                budget_per_day=None,
                arrival_time=None, departure_time=None,
                station_coord=None, hotel_coord=None,
                arrival_location=None, departure_location=None):
    """
    动态路线规划：
    - 有车站 → 第1天从车站出发，最后天到车站结束
    - 有酒店名/坐标 → 作为每天起终点（放行李/回酒店）
    - 两样都没有 → 简单地从酒店片区出发和结束
    """
    start = time.time()
    random.seed(42)
    if excluded_poi_ids is None: excluded_poi_ids = []
    if scored_ids is None: scored_ids = []
    if poi_scores is None: poi_scores = {}
    if hotel_coord is None:
        hotel_coord = DEFAULT_ACCOMMODATION.get(accommodation, DEFAULT_ACCOMMODATION["古城"])

    # 只保留用户在卡片阶段明确"想去"的（评分≥3），跳过和没选的不加入规划
    active = [p for p in pois if
              p["poi_id"] not in excluded_poi_ids and
              poi_scores.get(p["poi_id"], 0) >= 3]
    if not active:
        return {"routes": [], "excluded": [], "elapsed_ms": 0}

    dc = DistanceCache([p["poi_id"] for p in active])
    arr_min = _parse_time(arrival_time)
    dep_min = _parse_time(departure_time)
    cap = get_day_capacity(pace)

    # 评分排序
    def rank(p):
        us = poi_scores.get(p["poi_id"], 0)
        gr = p.get("rating", 0)
        return (200 + gr) if us >= 4 else (100 + gr) if us >= 3 else (50 + gr) if p["poi_id"] in scored_ids else gr

    sorted_pois = sorted(active, key=lambda p: -rank(p))

    # 天级分配
    groups = [[] for _ in range(days)]
    remain = [cap] * days
    for poi in sorted_pois:
        d = poi.get("duration_min", 90)
        best = -1
        for di in range(days):
            if remain[di] >= d and (best == -1 or remain[di] > remain[best]):
                best = di
        if best >= 0:
            groups[best].append(poi)
            remain[best] -= d

    excluded = []
    for poi in sorted_pois:
        if not any(poi["poi_id"] in [p["poi_id"] for p in g] for g in groups):
            excluded.append({"poi_id": poi["poi_id"], "name": poi.get("name", ""), "reason": "时间不足"})

    # ===== 日内排序 =====
    routes = []
    for di, grp in enumerate(groups):
        if not grp:
            routes.append({"day": di + 1, "items": [], "total_cost": 0, "total_walk": 0, "total_drive": 0, "pace": pace})
            continue

        seq = build_route_for_day(grp, dc, hotel_coord, cap, pace=pace)
        items = []
        total_cost = 0
        cursor = arr_min if (di == 0 and arr_min) else 8 * 60
        end_bound = dep_min if (di == days - 1 and dep_min) else 20 * 60

        have_station = station_coord is not None

        # ============ 每天起点 ============
        if di == 0 and have_station and arrival_location:
            # 第1天：车站 → 酒店
            items.append({
                "poi_id": "__arrival__",
                "name": f"🚉 抵达{arrival_location}",
                "type": "交通",
                "arrival_time": minutes_to_time(cursor),
                "departure_time": minutes_to_time(cursor + 5),
                "duration_min": 5, "avg_cost": 0, "travel_from_prev": 0,
                "lat": station_coord[0], "lon": station_coord[1],
            })
            t = travel_between(station_coord, hotel_coord, dc)
            cursor += t
            items.append({
                "poi_id": "__hotel__",
                "name": f"🏨 前往{accommodation}放行李",
                "type": "住宿",
                "arrival_time": minutes_to_time(cursor),
                "departure_time": minutes_to_time(cursor + 20),
                "duration_min": 20, "avg_cost": 0, "travel_from_prev": t,
                "lat": hotel_coord[0], "lon": hotel_coord[1],
            })
        elif di > 0:
            # 其他天：从酒店出发
            first_poi_lat = seq[0].get("lat", grp[0].get("lat", 0)) if seq else hotel_coord[0]
            first_poi_lon = seq[0].get("lon", grp[0].get("lon", 0)) if seq else hotel_coord[1]
            t = travel_between(hotel_coord, (first_poi_lat, first_poi_lon), dc) if seq else 0
            items.append({
                "poi_id": "__hotel_start__",
                "name": f"🏨 从{accommodation}出发",
                "type": "住宿",
                "arrival_time": minutes_to_time(cursor),
                "departure_time": minutes_to_time(cursor + 10),
                "duration_min": 10, "avg_cost": 0, "travel_from_prev": 0,
                "lat": hotel_coord[0], "lon": hotel_coord[1],
            })
            cursor += 10

        # ============ 游玩景点 ============
        for item in seq:
            poi = next((p for p in active if p["poi_id"] == item["poi_id"]), {})
            trav = item.get("travel_min", 0)

            if cursor + trav < end_bound:
                cursor += trav
            arrival = cursor
            dur = item.get("duration_min", poi.get("duration_min", 90))
            departure = min(arrival + dur, end_bound)

            items.append({
                "poi_id": item["poi_id"],
                "name": item.get("name", poi.get("name", "")),
                "type": poi.get("type", ""),
                "duration_min": dur,
                "arrival_time": minutes_to_time(arrival),
                "departure_time": minutes_to_time(departure),
                "avg_cost": poi.get("avg_cost", 0),
                "travel_from_prev": trav,
                "lat": poi.get("lat", 0), "lon": poi.get("lon", 0),
            })

            cursor = departure + 15
            total_cost += poi.get("avg_cost", 0)
            if cursor >= end_bound:
                break

        # ============ 每天终点 ============
        if items and not (di == 0 and len(items) == 2 and items[0]["poi_id"] == "__arrival__"):
            if di == days - 1 and have_station and departure_location:
                # 最后天：回酒店拿行李 → 去车站
                if cursor + travel_between(hotel_coord, station_coord, dc) < 24 * 60:
                    back_hotel = travel_between(
                        (items[-1]["lat"], items[-1]["lon"]), hotel_coord, dc)
                    cursor += back_hotel
                    items.append({
                        "poi_id": "__hotel_end__",
                        "name": f"🏨 回{accommodation}拿行李",
                        "type": "住宿",
                        "arrival_time": minutes_to_time(cursor),
                        "departure_time": minutes_to_time(cursor + 20),
                        "duration_min": 20, "avg_cost": 0, "travel_from_prev": back_hotel,
                        "lat": hotel_coord[0], "lon": hotel_coord[1],
                    })
                    to_station = travel_between(hotel_coord, station_coord, dc)
                    cursor += to_station
                    items.append({
                        "poi_id": "__departure__",
                        "name": f"🚉 前往{departure_location}（{minutes_to_time(dep_min)}前到）",
                        "type": "交通",
                        "arrival_time": minutes_to_time(cursor),
                        "departure_time": minutes_to_time(min(cursor, dep_min)),
                        "duration_min": 5, "avg_cost": 0, "travel_from_prev": to_station,
                        "lat": station_coord[0], "lon": station_coord[1],
                    })
            elif have_station or hotel_coord:
                # 中间天：回酒店休息
                back = travel_between(
                    (items[-1]["lat"], items[-1]["lon"]), hotel_coord, dc)
                if cursor + back < end_bound + 60:
                    cursor += back
                    items.append({
                        "poi_id": "__hotel_end__",
                        "name": f"🏨 回{accommodation}休息",
                        "type": "住宿",
                        "arrival_time": minutes_to_time(cursor),
                        "departure_time": minutes_to_time(cursor + 10),
                        "duration_min": 10, "avg_cost": 0, "travel_from_prev": back,
                        "lat": hotel_coord[0], "lon": hotel_coord[1],
                    })

        routes.append({
            "day": di + 1, "items": items, "total_cost": total_cost,
            "total_walk": 0,
            "total_drive": sum(it.get("travel_from_prev", 0) for it in items),
            "pace": pace,
        })

    return {
        "routes": routes, "excluded": excluded,
        "elapsed_ms": round((time.time() - start) * 1000),
    }

"""
T3: 约束检查模块
时间窗、日容量、用餐窗口等约束
"""

# 紧凑/标准/休闲 日容量(分钟)
DAY_CAPACITY = {
    "compact": 480,   # 8h
    "standard": 420,  # 7h
    "relaxed": 360,   # 6h
}

# 午餐窗
LUNCH_WINDOW = (11 * 60 + 30, 13 * 60)  # 11:30 ~ 13:00  (分钟从午夜)
# 晚餐窗
DINNER_WINDOW = (17 * 60 + 30, 19 * 60)  # 17:30 ~ 19:00


def time_to_minutes(t_str: str) -> int:
    """HH:MM → 分钟数"""
    if not t_str or ":" not in t_str:
        return 0
    parts = t_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def minutes_to_time(m: int) -> str:
    """分钟数 → HH:MM"""
    h = m // 60
    mi = m % 60
    return f"{h:02d}:{mi:02d}"


def get_day_capacity(pace: str = "relaxed") -> int:
    """根据游玩节奏获取日容量(分钟)"""
    return DAY_CAPACITY.get(pace, 360)


def fits_time_window(arrival_min: int, departure_min: int,
                     poi_open: str, poi_close: str) -> bool:
    """检查POI是否在营业时间内"""
    open_min = time_to_minutes(poi_open)
    close_min = time_to_minutes(poi_close)
    return arrival_min >= open_min and departure_min <= close_min


def get_accommodation_location(accommodation: str = "古城") -> tuple:
    """根据用户住宿偏好返回坐标"""
    locations = {
        "古城": (25.6814, 100.1647),
        "双廊": (25.9527, 100.1276),
        "喜洲": (25.8543, 100.0120),
        "海东": (25.5970, 100.2805),
        "才村": (25.6650, 100.1820),
        "苍山": (25.6667, 100.1000),
        "市中心": (25.6065, 100.2299),
    }
    return locations.get(accommodation, locations["古城"])


def get_lunch_poi_id(day_pois: list[dict], distance_cache=None) -> int | None:
    """在当日POI中找美食POI作为午餐候选，返回索引"""
    for i, poi in enumerate(day_pois):
        if poi.get("type") == "美食":
            return i
    return None


def validate_route(route: list[dict], day_capacity: int,
                   distance_cache, accommodation_loc: tuple) -> list[str]:
    """验证完整路线，返回违反的约束列表"""
    violations = []
    total_activity = sum(p.get("duration_min", 60) for p in route)
    total_travel = 0

    # 从头到尾的顺序
    ordered = route.copy()

    for i, poi in enumerate(ordered):
        # 交通时间
        if i == 0:
            # 从住宿出发
            travel = distance_cache.estimate(
                accommodation_loc[0], accommodation_loc[1],
                poi["lat"], poi["lon"]
            ) if distance_cache else 20
        else:
            prev = ordered[i - 1]
            travel = distance_cache.get(prev["poi_id"], poi["poi_id"]) if distance_cache else None
            if travel is None:
                travel = distance_cache.estimate(
                    prev["lat"], prev["lon"],
                    poi["lat"], poi["lon"]
                ) if distance_cache else 20
        total_travel += travel

    total = total_activity + total_travel
    if total > day_capacity:
        violations.append(f"总耗时{total}分钟超过日容量{day_capacity}分钟")

    return violations

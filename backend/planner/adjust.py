"""
T3/T7: 日内路线构建 + 2-opt 优化 + 调整逻辑
"""
import random
from backend.planner.distance import DistanceCache
from backend.planner.constraints import get_accommodation_location


def build_route_for_day(pois: list[dict], dist_cache: DistanceCache,
                        acc_loc: tuple[float, float], day_capacity: int,
                        pace: str = "relaxed") -> list[dict]:
    """
    构建单日路线：插入启发式 + 2-opt优化

    返回: [{"poi_id": ..., "name": ..., "duration_min": ..., "travel_min": ...}, ...]
    """
    if len(pois) <= 1:
        return _build_simple_route(pois, dist_cache, acc_loc)

    # 第一步：插入启发式构造初始解
    route = _greedy_insertion(pois, dist_cache, acc_loc)

    # 第二步：2-opt 局部优化（100轮）
    route = _two_opt(route, dist_cache, iterations=100)

    return route


def _build_simple_route(pois, dist_cache, acc_loc):
    items = []
    for i, poi in enumerate(pois):
        prev_travel = dist_cache.estimate(acc_loc[0], acc_loc[1], poi.get("lat", 0), poi.get("lon", 0)) if i == 0 else 0
        items.append({
            "poi_id": poi["poi_id"],
            "name": poi.get("name", ""),
            "duration_min": poi.get("duration_min", 120),
            "travel_min": prev_travel,
            "next_travel": 0,
        })
    return items


def _greedy_insertion(pois, dist_cache, acc_loc):
    """
    插入启发式：从最近的一个开始，每次选择插入后总时间增加最少的POI
    """
    if not pois:
        return []

    # 找距离住宿最近的POI作为起点
    first = min(pois, key=lambda p: dist_cache.estimate(
        acc_loc[0], acc_loc[1], p.get("lat", 0), p.get("lon", 0)
    ))

    route = [first]
    remaining = [p for p in pois if p["poi_id"] != first["poi_id"]]

    while remaining:
        best_poi = None
        best_insert_cost = float("inf")
        best_insert_idx = 0

        for poi in remaining:
            for idx in range(len(route) + 1):
                insert_cost = _calc_insert_cost(route, poi, idx, dist_cache, acc_loc)
                if insert_cost < best_insert_cost:
                    best_insert_cost = insert_cost
                    best_poi = poi
                    best_insert_idx = idx

        if best_poi:
            route.insert(best_insert_idx, best_poi)
            remaining.remove(best_poi)

    # 计算每段交通时间
    result = []
    for i, poi in enumerate(route):
        prev_travel = _get_travel(route[i - 1], poi, dist_cache) if i > 0 else \
            dist_cache.estimate(acc_loc[0], acc_loc[1], poi.get("lat", 0), poi.get("lon", 0))
        next_travel = _get_travel(poi, route[i + 1], dist_cache) if i < len(route) - 1 else 0
        result.append({
            "poi_id": poi["poi_id"],
            "name": poi.get("name", ""),
            "duration_min": poi.get("duration_min", 120),
            "travel_min": prev_travel,
            "next_travel": next_travel,
        })

    return result


def _calc_insert_cost(route, poi, insert_idx, dist_cache, acc_loc):
    """计算在指定位置插入POI所增加的时间成本"""
    poi_lat, poi_lon = poi.get("lat", 0), poi.get("lon", 0)

    if not route:
        return dist_cache.estimate(acc_loc[0], acc_loc[1], poi_lat, poi_lon)

    if insert_idx == 0:
        # 插在开头
        first = route[0]
        cost = dist_cache.estimate(acc_loc[0], acc_loc[1], poi_lat, poi_lon)
        cost += _get_travel(poi, first, dist_cache)
        # 减去原来的第一段
        cost -= dist_cache.estimate(acc_loc[0], acc_loc[1],
                                    first.get("lat", 0), first.get("lon", 0))
    elif insert_idx >= len(route):
        # 插在末尾
        last = route[-1]
        cost = _get_travel(last, poi, dist_cache)
    else:
        # 插在中间
        before = route[insert_idx - 1]
        after = route[insert_idx]
        cost = _get_travel(before, poi, dist_cache) + _get_travel(poi, after, dist_cache)
        cost -= _get_travel(before, after, dist_cache)

    return cost


def _get_travel(a, b, dist_cache):
    """获取两点间交通时间，fallback到估算"""
    travel = dist_cache.get(a["poi_id"], b["poi_id"])
    if travel is not None:
        return travel
    return dist_cache.estimate(a.get("lat", 0), a.get("lon", 0),
                               b.get("lat", 0), b.get("lon", 0))


def _two_opt(route: list[dict], dist_cache: DistanceCache, iterations: int = 100) -> list[dict]:
    """
    2-opt 局部优化：交换路线中两个POI的位置
    如果交换后总旅行时间减少，则保留交换
    """
    if len(route) < 3:
        return route

    n = len(route)
    best_route = route.copy()

    for _ in range(iterations):
        i = random.randint(0, n - 2)
        j = random.randint(i + 1, n - 1)

        new_route = best_route.copy()
        new_route[i:j + 1] = reversed(new_route[i:j + 1])

        # 计算前后总旅行时间
        old_cost = _total_travel_cost(best_route, dist_cache)
        new_cost = _total_travel_cost(new_route, dist_cache)

        if new_cost < old_cost:
            best_route = new_route

    # 重建结果（含travel_min和next_travel）
    result = []
    for i, poi in enumerate(best_route):
        prev_travel = _get_travel(best_route[i - 1], poi, dist_cache) if i > 0 else 0
        next_travel = _get_travel(poi, best_route[i + 1], dist_cache) if i < len(best_route) - 1 else 0
        result.append({
            "poi_id": poi["poi_id"],
            "name": poi.get("name", ""),
            "duration_min": poi.get("duration_min", 120),
            "travel_min": prev_travel,
            "next_travel": next_travel,
        })
    return result


def _total_travel_cost(route, dist_cache):
    """计算路线总交通时间"""
    total = 0
    for i in range(1, len(route)):
        total += _get_travel(route[i - 1], route[i], dist_cache)
    return total


def incremental_adjust(current_routes: list[dict], action: str,
                       poi_id: str = None, pace: str = None,
                       all_pois: list[dict] = None) -> list[dict]:
    """
    增量调整行程（T7中使用）
    action: add / remove / change_pace / replan
    """
    if action == "remove":
        return _remove_poi_from_routes(current_routes, poi_id)
    elif action == "add":
        return _add_poi_to_routes(current_routes, poi_id, all_pois)
    return current_routes


def _remove_poi_from_routes(routes, poi_id):
    """从行程中删除POI"""
    for day in routes:
        day["items"] = [it for it in day.get("items", []) if it["poi_id"] != poi_id]
    return routes


def _add_poi_to_routes(routes, poi_id, all_pois):
    """将POI添加到行程中（放在第一天末尾）"""
    poi = next((p for p in (all_pois or []) if p["poi_id"] == poi_id), None)
    if poi and routes:
        routes[0].setdefault("items", []).append({
            "poi_id": poi["poi_id"],
            "name": poi.get("name", ""),
            "type": poi.get("type", ""),
            "duration_min": poi.get("duration_min", 120),
            "avg_cost": poi.get("avg_cost", 0),
            "arrival_time": "12:00",
            "departure_time": "14:00",
            "travel_from_prev": 15,
        })
    return routes

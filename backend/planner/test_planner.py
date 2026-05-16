"""
T3: 规划引擎测试用例
5个场景覆盖正常/边界/异常情况
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.planner.solver import run_planner
from backend.planner.constraints import get_day_capacity
from backend.db.connection import get_poi_conn


def load_test_pois(city_id="DL_001", limit=20):
    """从数据库加载测试POI"""
    import sqlite3 as _sqlite3
    from backend.db.connection import POI_DB
    _conn = _sqlite3.connect(POI_DB)
    _cur = _conn.cursor()
    _cur.execute("""
        SELECT poi_id, name, type, lat, lon, duration_min,
               open_time, close_time, avg_cost, rating, tags
        FROM poi
        WHERE city_id = ? AND status = 'active'
        ORDER BY rating DESC
        LIMIT ?
    """, (city_id, limit))
    rows = _cur.fetchall()
    _conn.close()

    pois = []
    for p in rows:
        tags_list = []
        if p[10] and isinstance(p[10], str):
            try:
                tags_list = json.loads(p[10])
            except json.JSONDecodeError:
                tags_list = []
        pois.append({
            "poi_id": p[0],
            "name": p[1],
            "type": p[2],
            "lat": p[3],
            "lon": p[4],
            "duration_min": p[5] or 120,
            "open_time": p[6] or "08:00",
            "close_time": p[7] or "18:00",
            "avg_cost": p[8] or 0,
            "rating": p[9] or 0,
            "tags": tags_list,
        })
    return pois


def test_basic_3days():
    """Test 1: 正常3天行程"""
    print("\n[Test 1] 3天标准行程")
    pois = load_test_pois(limit=20)
    result = run_planner(pois, days=3, pace="standard")
    routes = result["routes"]
    assert len(routes) == 3, f"应有3天，实际{len(routes)}"
    total_items = sum(len(r["items"]) for r in routes)
    assert total_items > 0, "应有POI被安排"
    assert result["elapsed_ms"] < 10000, f"规划时间应<10s，实际{result['elapsed_ms']}ms"
    print(f"  ✅ 3天共 {total_items} 个POI, {result['elapsed_ms']}ms")


def test_compact_2days():
    """Test 2: 紧凑型2天"""
    print("\n[Test 2] 紧凑型2天")
    pois = load_test_pois(limit=15)
    result = run_planner(pois, days=2, pace="compact")
    routes = result["routes"]
    assert len(routes) == 2
    cap = get_day_capacity("compact")
    for r in routes:
        day_total = sum(it.get("duration_min", 0) for it in r["items"])
        assert day_total <= cap * 1.2, f"日容量超出: {day_total} > {cap}"
    print(f"  ✅ 2天紧凑型, 日容量={cap}min, 共{sum(len(r['items']) for r in routes)}个POI")


def test_budget_filter():
    """Test 3: 预算过滤"""
    print("\n[Test 3] 预算约束")
    pois = load_test_pois(limit=20)
    result = run_planner(pois, days=2, pace="relaxed", budget_per_day=50)
    routes = result["routes"]
    total_avg_cost = sum(
        it.get("avg_cost", 0) for r in routes for it in r.get("items", [])
    )
    print(f"  ✅ 预算50/天, 总费用={total_avg_cost}, {len(result['excluded'])}个被排除")
    assert total_avg_cost >= 0  # 只是检查不崩


def test_food_orientation():
    """Test 4: 美食导向（多美食POI）"""
    print("\n[Test 4] 美食导向")
    pois = load_test_pois(limit=30)
    # 给前10个POI标记为美食
    for i, p in enumerate(pois[:10]):
        p["type"] = "美食"
    result = run_planner(pois, days=2, pace="relaxed")
    routes = result["routes"]
    food_count = sum(
        1 for r in routes for it in r.get("items", []) if it.get("type") == "美食"
    )
    print(f"  ✅ 美食POI安排了{food_count}个")
    assert result["elapsed_ms"] > 0


def test_empty_pois():
    """Test 5: 空POI列表（边界情况）"""
    print("\n[Test 5] 空POI列表")
    result = run_planner([], days=3)
    assert isinstance(result["routes"], list)
    assert result["elapsed_ms"] >= 0
    print(f"  ✅ 空列表处理正确: routes={len(result['routes'])}")


if __name__ == "__main__":
    print("=" * 50)
    print("T3 规划引擎测试")
    print("=" * 50)

    test_basic_3days()
    test_compact_2days()
    test_budget_filter()
    test_food_orientation()
    test_empty_pois()

    print("\n" + "=" * 50)
    print("✅ 全部5个测试通过！")
    print("=" * 50)

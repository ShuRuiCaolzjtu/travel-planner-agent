"""
T1: 数据完整性检查脚本
验证 poi_cache.db 和 distance.db 的数据完整性
"""

import sqlite3
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POI_DB = os.path.join(ROOT, "data", "poi_cache.db")
DIST_DB = os.path.join(ROOT, "data", "distance.db")


def check_poi_db():
    """检查POI数据库"""
    print("=" * 50)
    print("POI 数据库检查")
    print("=" * 50)

    if not os.path.exists(POI_DB):
        print(f"❌ 文件不存在: {POI_DB}")
        return False

    conn = sqlite3.connect(POI_DB)
    cur = conn.cursor()

    # 城市信息
    cur.execute("SELECT city_id, name, poi_count, status FROM city")
    cities = cur.fetchall()
    if not cities:
        print("❌ 城市表为空")
        conn.close()
        return False

    for city in cities:
        print(f"  城市: {city[0]} ({city[1]}) | POI数量: {city[2]} | 状态: {city[3]}")

    # POI统计
    cur.execute("SELECT COUNT(*) FROM poi")
    total_poi = cur.fetchone()[0]
    print(f"\n  POI总量: {total_poi}")

    cur.execute("SELECT type, COUNT(*) FROM poi GROUP BY type ORDER BY COUNT(*) DESC")
    type_stats = cur.fetchall()
    print(f"\n  类型分布:")
    for t, c in type_stats:
        print(f"    {t}: {c}")

    # 评分统计
    cur.execute("SELECT COUNT(*) FROM poi WHERE rating > 0")
    has_rating = cur.fetchone()[0]
    cur.execute("SELECT AVG(rating) FROM poi WHERE rating > 0")
    avg_rating = cur.fetchone()[0] or 0
    print(f"\n  有评分的POI: {has_rating}/{total_poi}")
    print(f"  平均评分(有评分): {avg_rating:.2f}")

    cur.execute("SELECT COUNT(*) FROM poi WHERE status='active'")
    active = cur.fetchone()[0]
    print(f"  Active POI: {active}")

    # 片区统计
    cur.execute("SELECT district, COUNT(*) FROM poi WHERE district != '其他' AND district != '' GROUP BY district ORDER BY COUNT(*) DESC")
    district_stats = cur.fetchall()
    if district_stats:
        print(f"\n  片区分布:")
        for d, c in district_stats:
            print(f"    {d}: {c}")

    # 抽样检查
    print(f"\n  --- 抽样检查(5条) ---")
    cur.execute("""
        SELECT poi_id, name, type, rating, avg_cost, district
        FROM poi ORDER BY rating DESC LIMIT 5
    """)
    for row in cur.fetchall():
        print(f"    {row[0]} | {row[1]} | {row[2]} | ⭐{row[3]} | ¥{row[4]} | {row[5]}")

    print(f"\n  ✅ poi_cache.db 检查完成: {total_poi} 条POI")
    conn.close()
    return True


def check_distance_db():
    """检查距离矩阵数据库"""
    print("\n" + "=" * 50)
    print("距离矩阵数据库检查")
    print("=" * 50)

    if not os.path.exists(DIST_DB):
        print(f"❌ 文件不存在: {DIST_DB}")
        return False

    conn = sqlite3.connect(DIST_DB)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM distance_matrix")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT from_poi_id) FROM distance_matrix")
    from_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT to_poi_id) FROM distance_matrix")
    to_count = cur.fetchone()[0]

    print(f"  总距离记录: {total}")
    print(f"  源POI数: {from_count}")
    print(f"  目标POI数: {to_count}")

    # 抽样检查
    print(f"\n  --- 抽样检查(3条) ---")
    poi_conn = sqlite3.connect(POI_DB)
    poi_cur = poi_conn.cursor()
    cur.execute("""
        SELECT from_poi_id, to_poi_id, drive_minutes, drive_distance
        FROM distance_matrix
        LIMIT 3
    """)
    for row in cur.fetchall():
        from_id, to_id, minutes, dist = row
        poi_cur.execute("SELECT name FROM poi WHERE poi_id=?", (from_id,))
        from_name = poi_cur.fetchone()
        from_name = from_name[0] if from_name else from_id
        poi_cur.execute("SELECT name FROM poi WHERE poi_id=?", (to_id,))
        to_name = poi_cur.fetchone()
        to_name = to_name[0] if to_name else to_id
        print(f"    {from_name} → {to_name}, 驾车 {minutes} 分钟 ({dist}m)")
    poi_conn.close()

    print(f"\n  {'✅' if total > 0 else '❌'} distance.db 检查完成: {total} 条记录")
    conn.close()
    return total > 0


def main():
    print("=" * 60)
    print("T1 数据完整性检查")
    print(f"  POI DB: {POI_DB}")
    print(f"  DIST DB: {DIST_DB}")
    print("=" * 60 + "\n")

    poi_ok = check_poi_db()
    dist_ok = check_distance_db()

    print("\n" + "=" * 60)
    if poi_ok and dist_ok:
        print("✅ 全部检查通过！")
    else:
        print("⚠️ 部分检查未通过:")
        if not poi_ok:
            print("  - poi_cache.db 异常")
        if not dist_ok:
            print("  - distance.db 异常")
    print("=" * 60)

    return 0 if (poi_ok and dist_ok) else 1


if __name__ == "__main__":
    sys.exit(main())

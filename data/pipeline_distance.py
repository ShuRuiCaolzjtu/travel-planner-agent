"""
T1: 离线距离矩阵构建脚本
从 poi_cache.db 读取POI，调用高德距离API逐个计算驾车时间
输出 distance.db
"""

import sqlite3
import time
import os
import requests

AMAP_KEY = "d7eb03b1cbcdc5673d74eb0d7ebe6eba"
DIST_API = "https://restapi.amap.com/v3/distance"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POI_DB = os.path.join(ROOT, "data", "poi_cache.db")
DIST_DB = os.path.join(ROOT, "data", "distance.db")

# 请求间隔(秒) - 个人开发者建议至少0.2s
REQUEST_INTERVAL = 0.2

# 每个类型的取量
def get_filtered_pois(conn):
    """获取LLM过滤后的高质量POI列表，取评分前50个"""
    cur = conn.cursor()
    cur.execute("""
        SELECT poi_id, name, lat, lon, type, rating, rating_count
        FROM poi
        WHERE status = 'active' AND llm_status = 'active'
        ORDER BY rating DESC, rating_count DESC
        LIMIT 50
    """)
    pois = cur.fetchall()
    print(f"  总计: {len(pois)} 个POI (LLM过滤后)")
    return pois


def build_distance_matrix():
    """主流程"""
    print("=" * 50)
    print("T1: 离线距离矩阵构建")
    print("=" * 50)

    # 读取POI
    print("\n[Step 1] 读取POI...")
    conn = sqlite3.connect(POI_DB)
    pois = get_filtered_pois(conn)
    conn.close()

    if len(pois) < 2:
        print("  POI不足，无法构建距离矩阵")
        return

    poi_list = []
    for p in pois:
        poi_list.append({
            "id": p[0],
            "name": p[1],
            "lat": p[2],  # p[2]=lat, p[3]=lon (来自SELECT顺序)
            "lon": p[3],
        })

    total_pairs = len(poi_list) * (len(poi_list) - 1) // 2
    print(f"  {len(poi_list)} 个POI × {len(poi_list)-1} 对 = {total_pairs} 个请求")

    # 打开距离DB
    os.makedirs(os.path.dirname(DIST_DB), exist_ok=True)
    dist_conn = sqlite3.connect(DIST_DB)
    dist_cur = dist_conn.cursor()
    dist_cur.execute("""
        CREATE TABLE IF NOT EXISTS distance_matrix (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_poi_id TEXT NOT NULL,
            to_poi_id TEXT NOT NULL,
            drive_minutes INTEGER,
            drive_distance INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(from_poi_id, to_poi_id)
        )
    """)
    dist_conn.commit()

    # 断点续传: 跳过已有记录
    dist_cur.execute("SELECT COUNT(*) FROM distance_matrix")
    existing = dist_cur.fetchone()[0]
    print(f"  已有记录: {existing} 条")

    computed = 0
    errors = 0
    skipped = 0

    print(f"\n[Step 2] 开始计算 (共{total_pairs}对)...")
    start_time = time.time()

    for i, src in enumerate(poi_list):
        for j, dst in enumerate(poi_list):
            if i >= j:  # 只算 i<j，减少请求量
                continue

            src_loc = f"{src['lon']},{src['lat']}"
            dst_loc = f"{dst['lon']},{dst['lat']}"

            # 检查是否已有记录
            dist_cur.execute(
                "SELECT 1 FROM distance_matrix WHERE from_poi_id=? AND to_poi_id=?",
                (src["id"], dst["id"])
            )
            if dist_cur.fetchone():
                skipped += 1
                continue

            # 调用API
            try:
                resp = requests.get(DIST_API, params={
                    "key": AMAP_KEY,
                    "origins": src_loc,
                    "destination": dst_loc,
                    "type": "1",
                }, timeout=15)
                data = resp.json()

                if data.get("status") == "1" and "results" in data:
                    result = data["results"][0]
                    try:
                        drive_dist = int(result.get("distance", 0))
                        drive_time = int(result.get("duration", 0))
                        drive_minutes = max(1, round(drive_time / 60))
                    except (ValueError, TypeError):
                        drive_minutes = None
                        drive_dist = None

                    # 写入正向和反向 (双向)
                    dist_cur.execute("""
                        INSERT OR IGNORE INTO distance_matrix
                        (from_poi_id, to_poi_id, drive_minutes, drive_distance)
                        VALUES (?, ?, ?, ?)
                    """, (src["id"], dst["id"], drive_minutes, drive_dist))
                    dist_cur.execute("""
                        INSERT OR IGNORE INTO distance_matrix
                        (from_poi_id, to_poi_id, drive_minutes, drive_distance)
                        VALUES (?, ?, ?, ?)
                    """, (dst["id"], src["id"], drive_minutes, drive_dist))
                    computed += 1
                else:
                    errors += 1
                    if errors <= 3:
                        print(f"  [警告] {src['name']}→{dst['name']}: {data.get('info','')}")

            except requests.exceptions.RequestException as e:
                errors += 1
                if errors <= 3:
                    print(f"  [警告] 请求失败: {e}")

            # 提交批处理
            if computed % 50 == 0 and computed > 0:
                dist_conn.commit()

            time.sleep(REQUEST_INTERVAL)

        # 每10个源POI打印进度
        if (i + 1) % 10 == 0:
            elapsed = time.time() - start_time
            pace = elapsed / (i + 1) if (i + 1) > 0 else 0
            print(f"  进度: 源{i+1}/{len(poi_list)} | 已算 {computed} 对 | 耗时 {elapsed:.0f}s | 均速 {pace:.1f}s/源")

    dist_conn.commit()

    elapsed = time.time() - start_time
    print(f"\n[Step 3] 完成")
    print(f"  已计算: {computed} 对")
    print(f"  跳过(已存在): {skipped} 对")
    print(f"  错误: {errors}")
    print(f"  总耗时: {elapsed:.0f}秒 ({elapsed/60:.1f}分钟)")

    dist_cur.execute("SELECT COUNT(*) FROM distance_matrix")
    total_stored = dist_cur.fetchone()[0]
    print(f"  distance.db 总记录: {total_stored} 条")
    print(f"  📍 数据库: {DIST_DB}")

    # 标记POI
    poi_ids_in_matrix = [p["id"] for p in poi_list]
    conn = sqlite3.connect(POI_DB)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE poi ADD COLUMN in_distance_matrix INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    cur.execute("UPDATE poi SET in_distance_matrix = 0")
    for pid in poi_ids_in_matrix:
        cur.execute("UPDATE poi SET in_distance_matrix = 1 WHERE poi_id = ?", (pid,))
    conn.commit()
    conn.close()

    dist_conn.close()


if __name__ == "__main__":
    build_distance_matrix()

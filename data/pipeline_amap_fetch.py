"""
T1: 高德POI采集脚本 v2 — 精确类型码+关键词搜索
只采集真正对游客有价值的POI
"""
import sqlite3
import time
import json
import os
import requests

AMAP_KEY = "d7eb03b1cbcdc5673d74eb0d7ebe6eba"
BASE_URL = "https://restapi.amap.com/v3"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "data", "poi_cache.db")

# ===== 精确类型码（只取对游客有价值的） =====
CATEGORIES = [
    # (type_code, local_type, description)
    ("120100", "景点", "风景名胜"),
    ("120200", "景点", "公园广场"),
    ("120300", "景点", "自然景观"),
    ("120400", "景点", "国家级景点"),
    ("120500", "景点", "省级景点"),
    ("080400", "景点", "寺庙道观"),
    ("080500", "景点", "教堂"),
    ("080300", "景点", "纪念馆"),
    ("090100", "景点", "公园"),
    ("110101", "景点", "美术馆"),
    ("110102", "景点", "展览馆"),
    ("110104", "景点", "科技馆"),
    ("110105", "景点", "博物馆"),
    ("110200", "景点", "国家级景点"),
    ("110300", "景点", "省级景点"),
]

# ===== 关键词搜索（补知名景點） =====
KEYWORD_SEARCHES = [
    ("景点", "大理必去景点"),
    ("景点", "大理旅游景点"),
    ("景点", "大理网红打卡地"),
    ("景点", "大理古城"),
    ("美食", "大理美食街"),
    ("美食", "大理小吃街"),
    ("活动", "大理特色体验"),
]

# 高德最多翻25页，每页25条
PAGE_SIZE = 25
MAX_PAGES = 25


def fetch_by_type(adcode, type_code, page=1):
    """按类型码搜索"""
    url = f"{BASE_URL}/place/text"
    params = {"key": AMAP_KEY, "city": adcode, "types": type_code,
              "offset": PAGE_SIZE, "page": page, "extensions": "all"}
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if data["status"] != "1":
            return [], 0
        total = int(data.get("count", 0))
        # 高德每类最多返回 25*25=625 条
        return data.get("pois", []), min(total, PAGE_SIZE * MAX_PAGES)
    except Exception:
        return [], 0


def fetch_by_keyword(adcode, keyword, page=1):
    """按关键词搜索"""
    url = f"{BASE_URL}/place/text"
    params = {"key": AMAP_KEY, "city": adcode, "keywords": keyword,
              "offset": PAGE_SIZE, "page": page, "extensions": "all"}
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if data["status"] != "1":
            return [], 0
        total = int(data.get("count", 0))
        return data.get("pois", []), min(total, PAGE_SIZE * MAX_PAGES)
    except Exception:
        return [], 0


def parse_opentime(opentime_str):
    if not opentime_str or opentime_str.strip() in ("", "全天开放", "00:00-24:00"):
        return "08:00", "18:00"
    opentime_str = opentime_str.strip()
    if "-" in opentime_str:
        parts = opentime_str.split("-")
        if len(parts) == 2:
            ot = parts[0].strip()[:5]
            ct = parts[1].strip()[:5]
            if ":" in ot and ":" in ct:
                return ot, ct
    import re
    m = re.search(r"(\d{1,2}:\d{2})-(\d{1,2}:\d{2})", opentime_str)
    if m:
        return m.group(1), m.group(2)
    return "08:00", "18:00"


def normalize_poi(poi, local_type, seen_names):
    """规范化单个POI记录"""
    name = poi.get("name", "").strip()
    if not name or name in seen_names:
        return None
    location = poi.get("location", "").strip()
    if not location or "," not in location:
        return None
    lon, lat = location.split(",")
    try:
        lon, lat = float(lon), float(lat)
    except ValueError:
        return None

    rating_str = poi.get("biz_ext", {}).get("rating", "0")
    try:
        rating = float(rating_str)
    except (ValueError, TypeError):
        rating = 0.0

    cost_str = poi.get("biz_ext", {}).get("cost", "0")
    try:
        cost = float(cost_str)
    except (ValueError, TypeError):
        cost = 0

    opentime = poi.get("opentime", "")
    open_t, close_t = parse_opentime(opentime)

    district = poi.get("business_area", "") or ""
    tag_str = poi.get("tag", "")
    tags = [t.strip() for t in tag_str.split(";") if t.strip()] if tag_str else []
    if rating >= 4.5:
        tags.append("高评分")

    seen_names.add(name)

    return {
        "name": name,
        "type": local_type,
        "lat": lat,
        "lon": lon,
        "duration_min": 90,
        "open_time": open_t,
        "close_time": close_t,
        "avg_cost": max(0, int(cost)),
        "rating": round(rating, 1),
        "rating_count": int(poi.get("biz_ext", {}).get("rating_count", 0)),
        "tags": json.dumps(tags, ensure_ascii=False),
        "summary": "",
        "district": district,
        "address": poi.get("address", ""),
        "status": "active",
    }


def main():
    print("=" * 50)
    print("T1: 高德POI采集 v2 — 精确类型码+关键词")
    print("=" * 50)

    # 获取大理adcode
    print("\n[Step 1] 获取大理行政区编码...")
    resp = requests.get(f"{BASE_URL}/config/district",
                        params={"keywords": "大理", "subdistrict": 0, "key": AMAP_KEY}, timeout=10)
    adcode = resp.json()["districts"][0]["adcode"]
    print(f"  adcode: {adcode}")

    all_pois = {}
    seen_names = set()

    # 策略1：类型码搜索
    print("\n[Step 2a] 按精确类型码搜索...")
    for type_code, local_type, desc in CATEGORIES:
        page = 1
        count = 0
        while page <= MAX_PAGES:
            pois, total = fetch_by_type(adcode, type_code, page)
            if not pois:
                break
            for poi in pois:
                record = normalize_poi(poi, local_type, seen_names)
                if record:
                    all_pois[record["name"]] = record
                    count += 1
            page += 1
            time.sleep(0.3)
        print(f"  {desc}({type_code}): {count}条")

    # 策略2：关键词搜索
    print("\n[Step 2b] 按关键词搜索（补知名景点）...")
    for local_type, keyword in KEYWORD_SEARCHES:
        page = 1
        count = 0
        while page <= MAX_PAGES:
            pois, total = fetch_by_keyword(adcode, keyword, page)
            if not pois:
                break
            for poi in pois:
                record = normalize_poi(poi, local_type, seen_names)
                if record:
                    all_pois[record["name"]] = record
                    count += 1
            page += 1
            time.sleep(0.3)
        print(f"  「{keyword}」: {count}条")

    print(f"\n去重后总计: {len(all_pois)} 个POI")

    # 写入SQLite
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 重建表
    cur.executescript("""
        DROP TABLE IF EXISTS poi;
        DROP TABLE IF EXISTS city;
        CREATE TABLE city (
            city_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            province TEXT,
            suggested_days TEXT,
            best_seasons TEXT,
            center_lat REAL,
            center_lon REAL,
            districts TEXT,
            poi_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE poi (
            poi_id TEXT PRIMARY KEY,
            city_id TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            lat REAL,
            lon REAL,
            duration_min INTEGER DEFAULT 120,
            open_time TEXT DEFAULT '08:00',
            close_time TEXT DEFAULT '18:00',
            avg_cost INTEGER DEFAULT 0,
            rating REAL DEFAULT 0,
            rating_count INTEGER DEFAULT 0,
            tags TEXT DEFAULT '[]',
            summary TEXT DEFAULT '',
            review_sources TEXT DEFAULT '[]',
            search_hotness INTEGER DEFAULT 0,
            cover_image TEXT DEFAULT '',
            gallery TEXT DEFAULT '[]',
            district TEXT DEFAULT '',
            address TEXT DEFAULT '',
            adcode TEXT DEFAULT '',
            need_booking INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            in_distance_matrix INTEGER DEFAULT 0,
            llm_summary TEXT DEFAULT '',
            llm_status TEXT DEFAULT 'pending'
        );
    """)

    # 插入城市
    cur.execute("""
        INSERT INTO city VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, ("DL_001", "大理", "云南", "[2,4]", "[3,4,5,9,10,11]",
          25.6065, 100.2299,
          json.dumps(["古城", "双廊", "喜洲", "海东", "才村", "苍山", "洱海"], ensure_ascii=False),
          len(all_pois), "active", time.strftime("%Y-%m-%dT%H:%M:%S")))

    # 插入POI
    poi_data = []
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    for idx, (name, poi) in enumerate(all_pois.items(), 1):
        poi_id = f"DL_POI_{idx:03d}"
        poi_data.append((
            poi_id, "DL_001", str(poi["name"]), str(poi["type"]),
            float(poi["lat"]), float(poi["lon"]), int(poi["duration_min"]),
            str(poi["open_time"]), str(poi["close_time"]), int(poi["avg_cost"]),
            float(poi["rating"]), int(poi["rating_count"]), str(poi["tags"]),
            str(poi["summary"]), "[]", int(poi["rating_count"]),
            "", "[]", str(poi["district"]),
            str(poi["address"]), str(adcode), 0, str(poi["status"]),
            now, 0, "", "pending"
        ))

    cur.executemany("""
        INSERT INTO poi (poi_id, city_id, name, type, lat, lon, duration_min,
            open_time, close_time, avg_cost, rating, rating_count, tags,
            summary, review_sources, search_hotness, cover_image, gallery,
            district, address, adcode, need_booking, status, created_at,
            in_distance_matrix, llm_summary, llm_status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, poi_data)

    conn.commit()
    conn.close()
    print(f"\n✅ poi_cache.db 写入完成: {len(poi_data)} 条POI")

    # 统计
    type_stats = {}
    for name, p in all_pois.items():
        t = p["type"]
        type_stats[t] = type_stats.get(t, 0) + 1
    print("\n类型分布:")
    for t, c in sorted(type_stats.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")


if __name__ == "__main__":
    main()

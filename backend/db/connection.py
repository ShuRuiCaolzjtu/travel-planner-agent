"""
T2: SQLite连接管理
"""
import sqlite3
import os
import threading

# 数据库路径
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
POI_DB = os.path.join(ROOT, "data", "poi_cache.db")
DIST_DB = os.path.join(ROOT, "data", "distance.db")
USER_DB = os.path.join(ROOT, "data", "user.db")

# 线程本地存储（每个请求线程独立连接）
_local = threading.local()


def get_poi_conn():
    """获取POI数据库连接"""
    if not hasattr(_local, "poi_conn") or _local.poi_conn is None:
        _local.poi_conn = sqlite3.connect(POI_DB)
        _local.poi_conn.row_factory = sqlite3.Row
    return _local.poi_conn


def get_dist_conn():
    """获取距离矩阵数据库连接"""
    if not hasattr(_local, "dist_conn") or _local.dist_conn is None:
        _local.dist_conn = sqlite3.connect(DIST_DB)
        _local.dist_conn.row_factory = sqlite3.Row
    return _local.dist_conn


def get_user_conn():
    """获取用户数据库连接（自动建表）"""
    if not hasattr(_local, "user_conn") or _local.user_conn is None:
        _local.user_conn = sqlite3.connect(USER_DB)
        _local.user_conn.row_factory = sqlite3.Row
        _init_user_db(_local.user_conn)
    return _local.user_conn


def _init_user_db(conn):
    """初始化用户数据库表"""
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS session (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            city_name TEXT,
            city_id TEXT,
            days INTEGER DEFAULT 3,
            current_phase TEXT DEFAULT 'city_input',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            expires_at TEXT DEFAULT (datetime('now','localtime','+24 hours'))
        );

        CREATE TABLE IF NOT EXISTS poi_score (
            score_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            poi_id TEXT NOT NULL,
            score INTEGER CHECK(score >= 1 AND score <= 5),
            gesture TEXT DEFAULT 'tap_star',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(session_id, poi_id)
        );

        CREATE TABLE IF NOT EXISTS user_preference (
            preference_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            num_people INTEGER,
            arrival_time TEXT,
            departure_time TEXT,
            accommodation TEXT DEFAULT '古城',
            transport_mode TEXT DEFAULT 'bus',
            pace TEXT DEFAULT 'relaxed',
            food_preference TEXT DEFAULT 'mixed',
            budget_per_day INTEGER,
            special_requirements TEXT,
            accommodation_lat REAL,
            accommodation_lon REAL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS planning_result (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            route_json TEXT NOT NULL,
            excluded_json TEXT,
            elapsed_ms INTEGER,
            is_adjusted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
    """)
    conn.commit()


def dict_from_row(row):
    """将sqlite3.Row转为dict"""
    if row is None:
        return None
    return dict(row)


def close_all():
    """清理所有连接"""
    for attr in ["poi_conn", "dist_conn", "user_conn"]:
        conn = getattr(_local, attr, None)
        if conn:
            conn.close()
            setattr(_local, attr, None)

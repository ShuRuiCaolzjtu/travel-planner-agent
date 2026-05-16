"""
T3: 距离矩阵查询模块
从 distance.db 读取驾车时间
"""
import sqlite3
import os
import math

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIST_DB = os.path.join(ROOT, "data", "distance.db")


class DistanceCache:
    """距离矩阵缓存（内存中加速查询）"""

    def __init__(self, poi_ids: list[str]):
        self._matrix = {}  # (from_id, to_id) -> minutes
        self._load(poi_ids)

    def _load(self, poi_ids: list[str]):
        """从SQLite加载距离矩阵"""
        if not os.path.exists(DIST_DB):
            self._empty = True
            return
        self._empty = False
        conn = sqlite3.connect(DIST_DB)
        cur = conn.cursor()
        # 批量加载所有相关POI的距离
        placeholders = ",".join("?" for _ in poi_ids)
        cur.execute(f"""
            SELECT from_poi_id, to_poi_id, drive_minutes
            FROM distance_matrix
            WHERE from_poi_id IN ({placeholders})
            AND to_poi_id IN ({placeholders})
        """, poi_ids + poi_ids)
        for from_id, to_id, minutes in cur.fetchall():
            self._matrix[(from_id, to_id)] = minutes
        conn.close()

    def get(self, from_id: str, to_id: str) -> int | None:
        """获取两点间驾车时间(分钟)，无数据返回None"""
        if self._empty:
            return None
        return self._matrix.get((from_id, to_id))

    def estimate(self, from_lat: float, from_lon: float,
                 to_lat: float, to_lon: float) -> int:
        """直线距离估算驾车时间(分钟)，作为距离矩阵缺失时的fallback"""
        # 球面距离 (Haversine) 米
        R = 6371000
        phi1, phi2 = math.radians(from_lat), math.radians(to_lat)
        dphi = math.radians(to_lat - from_lat)
        dlambda = math.radians(to_lon - from_lon)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist_m = R * c
        # 大理市区平均车速 ~30km/h，道路系数 1.4
        drive_minutes = (dist_m / 1000 / 30 * 60) * 1.4
        return max(1, round(drive_minutes))

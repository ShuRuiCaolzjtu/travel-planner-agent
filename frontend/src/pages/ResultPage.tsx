import { useState } from "react";
import { useSessionStore } from "../store/sessionStore";
import { api, type RouteDay } from "../api/client";
import RouteMap from "../components/RouteMap";

type Pace = "relaxed" | "standard" | "compact";

export default function ResultPage() {
  const { sessionId, routes, excluded, loading, runPlan } = useSessionStore();
  const [pace, setPace] = useState<Pace>("standard");

  const handleRemove = async (poiId: string) => {
    if (!sessionId) return;
    try {
      const result = await api.adjustPlanner(sessionId, "remove", poiId);
      // Refresh planner result
      runPlan();
    } catch (e) {
      console.error(e);
    }
  };

  const handleAdd = async (poiId: string) => {
    if (!sessionId) return;
    try {
      const result = await api.adjustPlanner(sessionId, "add", poiId);
      runPlan();
    } catch (e) {
      console.error(e);
    }
  };

  const handleChangePace = async (newPace: Pace) => {
    if (!sessionId) return;
    setPace(newPace);
    try {
      await api.adjustPlanner(sessionId, "change_pace", undefined, newPace);
      runPlan();
    } catch (e) {
      console.error(e);
    }
  };

  const handleReplan = () => {
    if (sessionId) runPlan();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[400px]">
        <div className="text-center">
          <div className="text-5xl mb-4 animate-bounce">🗺️</div>
          <p className="text-gray-500 text-lg">正在重新规划...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-4 space-y-4">
      <h1 className="text-2xl font-bold text-center">你的大理行程</h1>

      {/* 调整工具栏 */}
      <div className="flex items-center justify-between bg-white rounded-2xl shadow-sm p-4">
        <div className="flex gap-2">
          {(["relaxed", "standard", "compact"] as Pace[]).map((p) => (
            <button
              key={p}
              onClick={() => handleChangePace(p)}
              className={`px-3 py-1.5 text-sm rounded-lg font-medium transition ${
                pace === p
                  ? "bg-amber-500 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {p === "relaxed" ? "🌿 休闲" : p === "standard" ? "⚡ 标准" : "🚀 紧凑"}
            </button>
          ))}
        </div>
        <button
          onClick={handleReplan}
          className="text-sm text-amber-600 hover:text-amber-700 font-medium"
        >
          🔄 重新规划
        </button>
      </div>

      {routes.length === 0 && (
        <div className="text-center text-gray-400 py-8">
          <p>暂无行程数据，请先运行规划</p>
        </div>
      )}

      {/* 每日时间线 */}
      {routes.map((day) => (
        <div key={day.day} className="bg-white rounded-2xl shadow-md overflow-hidden">
          <div className="p-4 pb-0">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-bold">
                📅 第 {day.day} 天
              </h2>
              <span className="text-xs text-gray-400">
                💰 ¥{day.total_cost} | 🚗 {day.total_drive}分钟
              </span>
            </div>

            {/* 地图 + 时间线 */}
            <RouteMap
              pois={day.items.map(it => ({ name: it.name, lat: it.lat, lon: it.lon, arrival_time: it.arrival_time }))}
              day={day.day}
            />
            {/* 时间线 */}
              {day.items.map((item, i) => {
                // 判断时间段
                let period = "";
                const hour = parseInt(item.arrival_time?.split(":")[0] || "12");
                if (hour < 11) period = "🌅 上午";
                else if (hour < 14) period = "☀️ 中午";
                else if (hour < 17) period = "🌤️ 下午";
                else period = "🌙 傍晚";

                return (
                  <div key={i} className="relative pl-8 pb-4 border-l-2 border-amber-200 last:border-transparent">
                    {/* 时间点 */}
                    <div className="absolute left-0 top-0 -translate-x-1/2 w-3 h-3 rounded-full bg-amber-400 border-2 border-white" />

                    {/* 时间段标题 */}
                    {(i === 0 || parseInt(day.items[i - 1]?.arrival_time?.split(":")[0] || "0") / 4 !== Math.floor(hour / 4)) && (
                      <div className="text-xs text-amber-600 font-medium mb-1">{period}</div>
                    )}

                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-400 w-12">{item.arrival_time}</span>
                          <span className="font-medium text-sm">{item.name}</span>
                        </div>
                        <div className="flex items-center gap-3 mt-0.5 ml-12">
                          <span className="text-xs text-gray-400">🕐 {item.duration_min}分</span>
                          <span className="text-xs text-gray-400">💰 ¥{item.avg_cost}</span>
                          {item.travel_from_prev > 0 && (
                            <span className="text-xs text-gray-300">🚗 {item.travel_from_prev}分</span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => handleRemove(item.poi_id)}
                        className="text-gray-300 hover:text-red-500 transition px-1"
                        title="删除"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                );
              })}
        </div>
      </div>
      ))}

      {/* 未安排 POI 面板 */}
      {excluded.length > 0 && (
        <div className="bg-amber-50 rounded-2xl p-4">
          <h3 className="font-medium text-amber-800 mb-3 flex items-center gap-2">
            <span>⚠️</span>
            <span>未安排 — 时间不足或需要取舍</span>
          </h3>
          <div className="space-y-2">
            {excluded.map((e, i) => (
              <div
                key={i}
                className="flex items-center justify-between bg-white/70 rounded-xl px-3 py-2"
              >
                <div className="flex-1">
                  <span className="text-sm text-amber-900 font-medium">{e.name}</span>
                  <span className="text-xs text-amber-500 ml-2">— {e.reason}</span>
                </div>
                <button
                  onClick={() => handleAdd(e.poi_id)}
                  className="text-xs text-amber-600 hover:text-amber-700 font-medium px-2 py-1 rounded-lg hover:bg-amber-100 transition"
                >
                  + 加入
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 开始新规划 */}
      <div className="text-center py-4">
        <p className="text-xs text-gray-400">
          可以删除不想去的项目、从未安排列表添加回来、切换节奏一键重规划
        </p>
      </div>
    </div>
  );
}

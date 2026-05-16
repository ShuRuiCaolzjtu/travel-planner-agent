import { useState } from "react";
import { useSessionStore } from "../store/sessionStore";

export default function CityInput() {
  const { initSession, loading, error } = useSessionStore();
  const [city, setCity] = useState("大理");
  const [days, setDays] = useState(3);

  const handleStart = async () => {
    await initSession(city, days);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 px-4">
      <div className="text-center">
        <div className="text-6xl mb-4">🌏</div>
        <h1 className="text-3xl font-bold text-gray-800 mb-2">DIY旅行助手</h1>
        <p className="text-gray-400">输入目的地，开始规划你的自由行</p>
      </div>

      <div className="bg-white rounded-2xl shadow-lg p-6 w-full max-w-sm space-y-4">
        <div>
          <label className="text-sm text-gray-500 block mb-1">目的地</label>
          <input
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="w-full p-3 border border-gray-200 rounded-xl text-lg outline-none focus:border-amber-400"
            placeholder="比如：大理"
          />
        </div>

        <div>
          <label className="text-sm text-gray-500 block mb-1">游玩天数</label>
          <div className="flex gap-2">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                onClick={() => setDays(n)}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${
                  days === n
                    ? "bg-amber-500 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {n}天
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="text-red-500 text-sm bg-red-50 p-3 rounded-lg">{error}</div>
        )}

        <button
          onClick={handleStart}
          disabled={loading}
          className="w-full py-3 bg-gradient-to-r from-amber-500 to-rose-500 text-white rounded-xl font-bold shadow-lg hover:shadow-xl transition disabled:opacity-50"
        >
          {loading ? "加载中..." : "开始探索 →"}
        </button>
      </div>
    </div>
  );
}

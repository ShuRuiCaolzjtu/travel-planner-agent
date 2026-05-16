const BASE_URL = "http://127.0.0.1:8000/api/v1";

async function request<T>(path: string, options?: RequestInit, timeoutMs = 15000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const url = BASE_URL + path;
  try {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...options,
    });
    clearTimeout(timer);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "请求失败");
    return data.data as T;
  } catch (e: any) {
    clearTimeout(timer);
    if (e.name === "AbortError") throw new Error("请求超时，请检查后端是否在运行");
    throw e;
  }
}

export interface CityInfo {
  city_id: string;
  name: string;
  poi_count: number;
  suggested_days: string;
  best_seasons: string;
  center_lat: number;
  center_lon: number;
}

export interface POICard {
  poi_id: string;
  name: string;
  type: string;
  rating: number;
  rating_count: number;
  tags: string[];
  avg_cost: number;
  duration_min: number;
  district: string;
  lat: number;
  lon: number;
  summary: string;
  open_time?: string;
  close_time?: string;
}

export interface SessionData {
  session_id: string;
  phase: string;
  city: CityInfo;
  days: number;
}

export interface RouteDay {
  day: number;
  items: RouteItem[];
  total_cost: number;
  total_drive: number;
  pace: string;
}

export interface RouteItem {
  poi_id: string;
  name: string;
  type: string;
  duration_min: number;
  arrival_time: string;
  departure_time: string;
  avg_cost: number;
  travel_from_prev: number;
}

export interface PlannerResult {
  routes: RouteDay[];
  excluded: { poi_id: string; name: string; reason: string }[];
  elapsed_ms: number;
}

export interface ProfileData {
  num_people: number | null;
  pace: string | null;
  accommodation: string | null;
  transport_mode: string | null;
}

export const api = {
  createSession: (cityName: string, days: number) =>
    request<SessionData>("/session", {
      method: "POST",
      body: JSON.stringify({ city_name: cityName, days }),
    }),

  getCity: (name: string) => request<CityInfo>(`/city/${encodeURIComponent(name)}`),

  getCards: (sessionId: string, count = 3) =>
    request<{ cards: POICard[]; remaining: number }>(
      `/poi/cards?session_id=${sessionId}&count=${count}`
    ),

  scorePOI: (sessionId: string, poiId: string, score: number, gesture: string) =>
    request<void>(`/poi/${poiId}/score`, {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, score, gesture }),
    }),

  getPOIDetail: (poiId: string) => request<POICard & { gallery: string[] }>(`/poi/${poiId}`),

  getProfile: (sessionId: string) => request<ProfileData>(`/profile/${sessionId}`),

  updateProfile: (sessionId: string, data: Record<string, unknown>) =>
    request<void>(`/profile/${sessionId}`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  runPlanner: (sessionId: string) =>
    request<PlannerResult>("/planner/run", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    }, 30000),  // 规划最多等30秒

  adjustPlanner: (sessionId: string, action: string, poiId?: string, pace?: string) =>
    request<{ routes: RouteDay[]; changes: string[] }>("/planner/adjust", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, action, poi_id: poiId, pace }),
    }),

  getResult: (sessionId: string) => request<PlannerResult>(`/planner/result/${sessionId}`),
};

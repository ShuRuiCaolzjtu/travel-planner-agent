import React, { createContext, useContext, useState, useCallback } from "react";
import { api, type POICard, type RouteDay } from "../api/client";

interface SessionState {
  sessionId: string | null;
  cityName: string;
  days: number;
  phase: string;
  cards: POICard[];
  remaining: number;
  scoredCount: number;
  likeCount: number;
  routes: RouteDay[];
  excluded: { poi_id: string; name: string; reason: string }[];
  loading: boolean;
  error: string | null;

  initSession: (city: string, days: number) => Promise<void>;
  loadCards: () => Promise<void>;
  scoreCard: (poiId: string, score: number, gesture: string) => Promise<void>;
  runPlan: () => Promise<void>;
  setPhase: (p: string) => void;
}

const SessionContext = createContext<SessionState | null>(null);

export function useSessionStore() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSessionStore must be used within SessionProvider");
  return ctx;
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [cityName, setCityName] = useState("");
  const [days, setDays] = useState(3);
  const [phase, setPhase] = useState("city_input");
  const [cards, setCards] = useState<POICard[]>([]);
  const [remaining, setRemaining] = useState(0);
  const [scoredCount, setScoredCount] = useState(0);
  const [likeCount, setLikeCount] = useState(0);
  const [routes, setRoutes] = useState<RouteDay[]>([]);
  const [excluded, setExcluded] = useState<{ poi_id: string; name: string; reason: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initSession = useCallback(async (city: string, d: number) => {
    setLoading(true);
    setError(null);
    let session;
    try {
      session = await api.createSession(city, d);
      setSessionId(session.session_id);
      setCityName(city);
      setDays(d);
      setPhase(session.phase);
    } catch (e: unknown) {
      setLoading(false);
      setError(String(e));
      return;
    }
    // 加载卡片
    try {
      const data = await api.getCards(session.session_id, 3);
      setCards(data.cards);
      setRemaining(data.remaining);
      setLoading(false);
    } catch (e: unknown) {
      setLoading(false);
      setError(String(e));
    }
  }, []);

  const loadCards = useCallback(async (sid?: string) => {
    const id = sid || sessionId;
    if (!id) return;
    try {
      const data = await api.getCards(id, 3);
      setCards(data.cards);
      setRemaining(data.remaining);
    } catch (e: unknown) {
      setError(String(e));
    }
  }, [sessionId]);

  const scoreCard = useCallback(async (poiId: string, score: number, gesture: string) => {
    if (!sessionId) return;
    await api.scorePOI(sessionId, poiId, score, gesture);
    setScoredCount((c) => c + 1);
    // 右滑或评分>=4算"想去"
    if (score >= 4 || gesture === "swipe_right") {
      setLikeCount((c) => c + 1);
    }
    setCards((prev) => {
      const filtered = prev.filter((c) => c.poi_id !== poiId);
      return filtered;
    });
    try {
      const data = await api.getCards(sessionId, 3);
      setCards((prev) => {
        const existingIds = new Set(prev.map((c) => c.poi_id));
        const newCards = data.cards.filter((c) => !existingIds.has(c.poi_id));
        return [...prev, ...newCards];
      });
      setRemaining(data.remaining);
    } catch {
      // ignore
    }
  }, [sessionId]);

  const runPlan = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.runPlanner(sessionId);
      setRoutes(result.routes);
      setExcluded(result.excluded);
      setPhase("result");
      setLoading(false);
    } catch (e: unknown) {
      setLoading(false);
      setError(String(e));
    }
  }, [sessionId]);

  const value: SessionState = {
    sessionId, cityName, days, phase, cards, remaining, scoredCount, likeCount,
    routes, excluded, loading, error,
    initSession, loadCards, scoreCard, runPlan,
    setPhase,
  };

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
}

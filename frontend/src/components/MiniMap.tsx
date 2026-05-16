import { useEffect, useRef } from "react";

interface Props {
  lat: number;
  lon: number;
  name: string;
}

const KEY = "b94863475fb79861f527912a000a9b4b";

let mapApiLoaded = false;
let pendingCbs: (() => void)[] = [];

function loadApi(cb: () => void) {
  if ((window as any).AMap) { cb(); return; }
  if (mapApiLoaded) { pendingCbs.push(cb); return; }
  mapApiLoaded = true;
  pendingCbs.push(cb);
  const s = document.createElement("script");
  s.src = `https://webapi.amap.com/maps?v=2.0&key=${KEY}`;
  s.onload = () => { for (const fn of pendingCbs) fn(); pendingCbs = []; };
  document.head.appendChild(s);
}

export default function MiniMap({ lat, lon, name }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 拦截所有pointer事件，防止冒泡到SwipeableCard
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const stop = (e: Event) => e.stopPropagation();
    el.addEventListener("pointerdown", stop, true);
    el.addEventListener("pointermove", stop, true);
    el.addEventListener("pointerup", stop, true);
    return () => {
      el.removeEventListener("pointerdown", stop, true);
      el.removeEventListener("pointermove", stop, true);
      el.removeEventListener("pointerup", stop, true);
    };
  }, []);

  useEffect(() => {
    if (!ref.current) return;
    loadApi(() => {
      if (!ref.current || mapRef.current) return;
      const map = new (window as any).AMap.Map(ref.current, {
        zoom: 15,
        center: [lon, lat],
        mapStyle: "amap://styles/fresh",
        zooms: [3, 19],
        features: ["bg", "road", "building", "point"],
      });
      new (window as any).AMap.Marker({ position: [lon, lat], map });
      mapRef.current = map;
    });
  }, [lat, lon]);

  const zi = () => { const m = mapRef.current; if (m) m.setZoom(Math.min(19, (m.getZoom() || 15) + 1)); };
  const zo = () => { const m = mapRef.current; if (m) m.setZoom(Math.max(3, (m.getZoom() || 15) - 1)); };

  return (
    <div
      ref={containerRef}
      style={{ position: "relative", marginBottom: 12, borderRadius: 8, overflow: "hidden", height: 120, background: "#f1f5f9", touchAction: "none" }}
    >
      <div ref={ref} style={{ width: "100%", height: "100%" }} />
      {/* 阻止按钮事件冒泡 */}
      <div style={{ position: "absolute", right: 6, top: 6, display: "flex", flexDirection: "column", gap: 2 }}>
        <button onPointerDown={(e) => e.stopPropagation()} onClick={zi} style={{ width: 28, height: 28, borderRadius: 4, border: "1px solid #d1d5db", background: "#fff", fontSize: 16, cursor: "pointer" }}>＋</button>
        <button onPointerDown={(e) => e.stopPropagation()} onClick={zo} style={{ width: 28, height: 28, borderRadius: 4, border: "1px solid #d1d5db", background: "#fff", fontSize: 16, cursor: "pointer" }}>－</button>
      </div>
    </div>
  );
}

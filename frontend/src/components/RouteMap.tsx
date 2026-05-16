import { useEffect, useRef } from "react";

interface POI {
  name: string;
  lat: number;
  lon: number;
}

interface Props {
  pois: POI[];
  day: number;
}

const KEY = "b94863475fb79861f527912a000a9b4b";

export default function RouteMap({ pois, day }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const inited = useRef(false);

  useEffect(() => {
    if (!mapRef.current || pois.length === 0 || inited.current) return;

    const win = window as any;

    const draw = () => {
      inited.current = true;
      const map = new win.AMap.Map(mapRef.current!, {
        zoom: 13,
        center: [pois[0].lon, pois[0].lat],
        mapStyle: "amap://styles/fresh",
      });

      const markers = pois.map((p, i) => new win.AMap.Marker({
        position: [p.lon, p.lat],
        label: {
          content: `<div style="background:#f59e0b;color:#fff;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:bold;white-space:nowrap">${i + 1}. ${p.name}</div>`,
          direction: "top",
          offset: new win.AMap.Pixel(0, -4),
        },
      }));
      map.add(markers);

      if (pois.length >= 2) {
        win.AMap.plugin("AMap.Driving", () => {
          const driving = new win.AMap.Driving({
            map, panel: false, hideMarkers: true,
            policy: win.AMap.DrivingPolicy.LEAST_TIME,
          });
          const pts = pois.map((p) => new win.AMap.LngLat(p.lon, p.lat));
          driving.search(pts[0], pts[pts.length - 1], {
            waypoints: pts.slice(1, -1),
          });
        });
      }

      map.setFitView(undefined, false, [60, 60, 60, 60]);
    };

    if (!win.AMap) {
      const s = document.createElement("script");
      s.src = `https://webapi.amap.com/maps?v=2.0&key=${KEY}`;
      s.onload = draw;
      document.head.appendChild(s);
    } else {
      draw();
    }
  }, []);

  return (
    <div style={{ borderRadius: 12, overflow: "hidden", border: "1px solid #e2e8f0" }}>
      <div ref={mapRef} style={{ width: "100%", height: 300, backgroundColor: "#f1f5f9" }} />
      <div style={{ padding: "8px 12px", fontSize: 12, color: "#94a3b8", backgroundColor: "#f8fafc", borderTop: "1px solid #e2e8f0" }}>
        第{day}天 · {pois.length}个去处 · 蓝色路网为驾车导航路径
      </div>
    </div>
  );
}

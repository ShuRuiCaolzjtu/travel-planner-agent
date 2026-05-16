import type { POICard } from "../api/client";
import PoiCard from "./PoiCard";

interface Props {
  cards: POICard[];
  onSwipeLeft: (poiId: string) => void;
  onSwipeRight: (poiId: string) => void;
  onSwipeUp: (poiId: string) => void;
  onSwipeDown: (poiId: string) => void;
  onStar: (poiId: string, score: number) => void;
}

export default function CardDeck({ cards, onSwipeLeft, onSwipeRight, onSwipeUp, onSwipeDown, onStar }: Props) {
  if (cards.length === 0) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 460, width: 340, backgroundColor: "#f9fafb", borderRadius: 20 }}>
        <div style={{ textAlign: "center", color: "#9ca3af" }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📭</div>
          <p style={{ fontSize: 14 }}>没有更多卡片了</p>
          <p style={{ fontSize: 12, marginTop: 8 }}>点击「开始排程」进入下一步</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ position: "relative", width: 340, height: 520, margin: "0 auto" }}>
      {cards.map((card, index) => (
        <div
          key={card.poi_id}
          style={{
            zIndex: cards.length - index,
            transform: `scale(${1 - index * 0.03}) translateY(${index * 8}px)`,
            position: "absolute",
            width: "100%",
            top: 0,
            left: 0,
          }}
        >
          {index === 0 ? (
            <PoiCard
              card={card}
              onSwipeLeft={() => onSwipeLeft(card.poi_id)}
              onSwipeRight={() => onSwipeRight(card.poi_id)}
              onSwipeUp={() => onSwipeUp(card.poi_id)}
              onSwipeDown={() => onSwipeDown(card.poi_id)}
              onStar={(score) => onStar(card.poi_id, score)}
            />
          ) : (
            <div style={{ backgroundColor: "#fff", borderRadius: 20, boxShadow: "0 4px 12px rgba(0,0,0,0.08)", width: "100%", height: 460, display: "flex", alignItems: "center", justifyContent: "center", color: "#9ca3af" }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>
                  {card.type === "景点" ? "🏔️" : card.type === "美食" ? "🍜" : "🎯"}
                </div>
                <p style={{ fontSize: 13 }}>{card.name}</p>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

import type { POICard } from "../api/client";
import SwipeableCard from "./SwipeableCard";
import MiniMap from "./MiniMap";
import { useState } from "react";

interface Props {
  card: POICard;
  onSwipeLeft: () => void;
  onSwipeRight: () => void;
  onSwipeUp: () => void;
  onSwipeDown: () => void;
  onStar: (score: number) => void;
}

export default function PoiCard({
  card, onSwipeLeft, onSwipeRight, onSwipeUp, onSwipeDown, onStar,
}: Props) {
  const [showStars, setShowStars] = useState(false);
  const tags = Array.isArray(card.tags) ? card.tags.slice(0, 4) : [];

  const typeColor = card.type === "景点" ? "#059669" : card.type === "美食" ? "#ea580c" : card.type === "活动" ? "#2563eb" : "#7c3aed";

  return (
    <SwipeableCard
      onSwipeLeft={onSwipeLeft}
      onSwipeRight={onSwipeRight}
      onSwipeUp={onSwipeUp}
      onSwipeDown={onSwipeDown}
    >
      <div
        style={{
          backgroundColor: "#fff",
          borderRadius: 20,
          boxShadow: "0 8px 30px rgba(0,0,0,0.12)",
          width: "100%",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          position: "relative",
        }}
      >
        {/* 顶部渐变封面 */}
        <div
          style={{
            height: 140,
            background: "linear-gradient(135deg, #dbeafe, #e0e7ff)",
            padding: "16px 20px",
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
          }}
        >
          <span
            style={{
              fontSize: 13,
              color: typeColor,
              backgroundColor: "rgba(255,255,255,0.9)",
              padding: "4px 12px",
              borderRadius: 20,
              fontWeight: 600,
            }}
          >
            {card.type === "景点" ? "🏔 " : card.type === "美食" ? "🍜 " : card.type === "活动" ? "🎯 " : "🛍 "}{card.type}
          </span>
          <span style={{ fontSize: 13, color: "#6b7280" }}>{card.district || "大理"}</span>
        </div>

        {/* 内容 */}
        <div style={{ padding: "20px 20px 16px", textAlign: "left" }}>
          {/* 名称 */}
          <h2 style={{ fontSize: 20, fontWeight: 700, color: "#1e293b", margin: "0 0 10px 0", lineHeight: 1.3 }}>
            {card.name}
          </h2>

          {/* 可缩放小地图 */}
          <MiniMap lat={card.lat} lon={card.lon} name={card.name} />

          {/* 评分行 */}
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
            <span style={{ color: "#f59e0b", fontSize: 15, letterSpacing: 2 }}>
              {"★".repeat(Math.round(card.rating))}{"☆".repeat(5 - Math.round(card.rating))}
            </span>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#1e293b" }}>{card.rating.toFixed(1)}</span>
            <span style={{ color: "#d1d5db", margin: "0 4px" }}>·</span>
            <span style={{ fontSize: 13, color: "#6b7280" }}>{card.rating_count}人评价</span>
          </div>

          {/* 时长费用行 */}
          <div style={{ display: "flex", gap: 16, fontSize: 13, color: "#6b7280", marginBottom: 16, paddingBottom: 12, borderBottom: "1px solid #f1f5f9" }}>
            <span>🕐 {card.duration_min}分钟</span>
            <span>💰 ¥{card.avg_cost}</span>
          </div>

          {/* 标签 */}
          {tags.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
              {tags.map((t, i) => (
                <span key={i} style={{ fontSize: 12, backgroundColor: "#f1f5f9", color: "#64748b", padding: "3px 10px", borderRadius: 12 }}>
                  {t}
                </span>
              ))}
            </div>
          )}

          {/* 摘要 */}
          <p style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.6, margin: "0 0 14px 0", flex: 1 }}>
            {card.summary || `${card.type} · 建议${card.duration_min}分钟`}
          </p>

          {/* 评分按钮 */}
          {!showStars ? (
            <button
              onClick={() => setShowStars(true)}
              style={{ fontSize: 13, color: "#9ca3af", border: "none", background: "none", cursor: "pointer", padding: 0, display: "flex", alignItems: "center", gap: 4 }}
            >
              ⭐ 给这个去处打分
            </button>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ fontSize: 13, color: "#9ca3af", marginRight: 6 }}>评分：</span>
              {[1, 2, 3, 4, 5].map((s) => (
                <button
                  key={s}
                  onClick={() => { onStar(s); setShowStars(false); }}
                  style={{ fontSize: 22, border: "none", background: "none", cursor: "pointer", padding: "0 2px" }}
                >
                  {s <= card.rating ? "⭐" : "☆"}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 底部手势提示 */}
        <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 20px", backgroundColor: "#fafafa", borderTop: "1px solid #f1f5f9", fontSize: 12, color: "#cbd5e1" }}>
          <span>👈 跳过</span>
          <span>👆 详情</span>
          <span>👉 想去</span>
        </div>
      </div>
    </SwipeableCard>
  );
}

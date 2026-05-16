import React, { useRef, useEffect, useState } from "react";

interface Props {
  children: React.ReactNode;
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
}

export default function SwipeableCard({ children, onSwipeLeft, onSwipeRight }: Props) {
  const elRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef({ startX: 0, lastX: 0, dragging: false, swiped: false });
  const [dx, setDx] = useState(0);
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    const el = elRef.current;
    if (!el) return;

    const onDown = (e: PointerEvent) => {
      if (dragRef.current.swiped) return;
      dragRef.current = { startX: e.clientX, lastX: e.clientX, dragging: true, swiped: false };
      setDx(0);
      setLeaving(false);
      el.setPointerCapture(e.pointerId);
    };

    const onMove = (e: PointerEvent) => {
      if (!dragRef.current.dragging) return;
      dragRef.current.lastX = e.clientX;
      setDx(e.clientX - dragRef.current.startX);
    };

    const onUp = (e: PointerEvent) => {
      if (!dragRef.current.dragging || dragRef.current.swiped) return;
      dragRef.current.dragging = false;
      const delta = e.clientX - dragRef.current.startX;
      const threshold = 60;

      if (delta > threshold) {
        dragRef.current.swiped = true;
        setDx(600);
        setLeaving(true);
        setTimeout(() => onSwipeRight?.(), 250);
      } else if (delta < -threshold) {
        dragRef.current.swiped = true;
        setDx(-600);
        setLeaving(true);
        setTimeout(() => onSwipeLeft?.(), 250);
      } else {
        setDx(0);
      }
    };

    el.addEventListener("pointerdown", onDown);
    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerup", onUp);
    el.addEventListener("pointercancel", onUp);
    el.addEventListener("pointerleave", onUp);

    return () => {
      el.removeEventListener("pointerdown", onDown);
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerup", onUp);
      el.removeEventListener("pointercancel", onUp);
      el.removeEventListener("pointerleave", onUp);
    };
  }, [onSwipeLeft, onSwipeRight]);

  const rotation = dx * 0.05;

  return (
    <div
      ref={elRef}
      style={{
        touchAction: "none",
        transform: `translateX(${dx}px) rotate(${rotation}deg)`,
        transition: leaving ? "transform 0.25s ease" : dx === 0 && !leaving ? "transform 0.2s ease" : "none",
        cursor: dragRef.current.dragging ? "grabbing" : "grab",
        userSelect: "none",
        position: "relative",
      }}
    >
      {/* 左滑指示 - 跳过 */}
      <div
        style={{
          position: "absolute",
          top: 24,
          right: 24,
          zIndex: 10,
          padding: "6px 14px",
          borderRadius: 10,
          fontWeight: 700,
          fontSize: 16,
          border: "2px solid #ef4444",
          color: "#ef4444",
          backgroundColor: "rgba(255,255,255,0.9)",
          opacity: Math.min(1, Math.max(0, -dx / 80)),
          pointerEvents: "none",
          transition: "opacity 0.1s",
        }}
      >
        ✕ 跳过
      </div>

      {/* 右滑指示 - 想去 */}
      <div
        style={{
          position: "absolute",
          top: 24,
          left: 24,
          zIndex: 10,
          padding: "6px 14px",
          borderRadius: 10,
          fontWeight: 700,
          fontSize: 16,
          border: "2px solid #22c55e",
          color: "#22c55e",
          backgroundColor: "rgba(255,255,255,0.9)",
          opacity: Math.min(1, Math.max(0, dx / 80)),
          pointerEvents: "none",
          transition: "opacity 0.1s",
        }}
      >
        ❤️ 想去
      </div>

      {children}
    </div>
  );
}

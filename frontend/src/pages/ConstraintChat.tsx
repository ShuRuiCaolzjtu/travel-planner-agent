import React, { useState, useEffect, useRef } from "react";
import { useSessionStore } from "../store/sessionStore";

const API = "/api/v1";

export default function ConstraintChat() {
  const { sessionId, runPlan, setPhase } = useSessionStore();
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([]);
  const [input, setInput] = useState("");
  const [finished, setFinished] = useState(false);
  const [planning, setPlanning] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sessionId) return;
    // 开始约束对话
    fetch(`${API}/constraint/start/${sessionId}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.ok) {
          setMessages([{ role: "agent", text: data.data.question }]);
        }
      });
  }, [sessionId]);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || !sessionId) return;

    const newMsgs = [...messages, { role: "user", text }];
    setMessages(newMsgs);
    setInput("");

    try {
      const r = await fetch(`${API}/constraint/chat/${sessionId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await r.json();
      if (data.ok) {
        setMessages((prev) => [
          ...prev,
          { role: "agent", text: data.data.question },
        ]);

        if (data.data.conflicts?.length > 0) {
          // 单独显示冲突
          setMessages((prev) => [
            ...prev,
            { role: "agent", text: `⚠️ ${data.data.conflicts.join("\n")}` },
          ]);
        }

        if (data.data.finished) {
          setFinished(true);
          // 自动触发规划
          setPlanning(true);
          setTimeout(async () => {
            await runPlan();
          }, 500);
        }
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "agent", text: "网络出了点问题，请再试一次~" },
      ]);
    }
  };

  if (planning) {
    return (
      <div className="flex items-center justify-center h-[400px]">
        <div className="text-center">
          <div className="text-5xl mb-4 animate-bounce">🗺️</div>
          <p className="text-gray-500 text-lg">正在规划最优路线...</p>
          <p className="text-gray-400 text-sm mt-2">结合你的偏好和实时距离计算中</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto p-4 flex flex-col h-[600px]">
      <div
        ref={chatRef}
        className="flex-1 overflow-y-auto space-y-3 mb-4 px-2"
      >
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] p-3 rounded-2xl text-sm whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-amber-500 text-white rounded-br-md"
                  : "bg-gray-100 text-gray-800 rounded-bl-md"
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
      </div>

      {!finished && (
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage(input)}
            placeholder="随便说，像聊天一样..."
            className="flex-1 p-3 border border-gray-200 rounded-xl text-sm outline-none focus:border-amber-400"
          />
          <button
            onClick={() => sendMessage(input)}
            className="px-4 py-2 bg-amber-500 text-white rounded-xl font-medium"
          >
            发送
          </button>
        </div>
      )}
    </div>
  );
}

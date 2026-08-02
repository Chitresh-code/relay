import type { FormEvent } from "react";
import { useEffect, useRef } from "react";
import { Streamdown } from "streamdown";
import type { Theme } from "../theme";
import type { ChatMessage } from "../types";
import { ComponentCard } from "./ComponentCard";

function TypingIndicator({ t }: { t: Theme }) {
  return (
    <div style={{ display: "flex", gap: 5, padding: "6px 2px" }}>
      {[0, 0.15, 0.3].map((delay) => (
        <span
          key={delay}
          style={{
            width: 6,
            height: 6,
            borderRadius: 999,
            background: t.accent,
            display: "inline-block",
            animation: `relay-bounce 1.1s infinite ${delay}s`,
          }}
        />
      ))}
    </div>
  );
}

export function ChatView({
  t,
  sessionId,
  messages,
  isTyping,
  input,
  onInputChange,
  onSubmit,
  onReset,
}: {
  t: Theme;
  sessionId: string;
  messages: ChatMessage[];
  isTyping: boolean;
  input: string;
  onInputChange: (v: string) => void;
  onSubmit: (e: FormEvent) => void;
  onReset: () => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);

  useEffect(() => {
    const el = scrollRef.current;
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight;
  }, [messages, isTyping]);

  function handleScroll() {
    const el = scrollRef.current;
    if (!el) return;
    // only keep auto-scrolling if the user hasn't deliberately scrolled away from the bottom
    stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", boxSizing: "border-box" }}>
      <div
        style={{
          padding: "16px 150px 16px 22px", // right padding clears the fixed theme toggle (App.tsx)
          borderBottom: `1px solid ${t.ruleColor}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: t.panelBg,
        }}
      >
        <div
          style={{
            font: "12px 'JetBrains Mono',monospace",
            color: t.textMuted,
            textTransform: "uppercase",
            letterSpacing: ".08em",
          }}
        >
          session · relay
        </div>
        <button
          onClick={onReset}
          style={{
            border: `1px solid ${t.panelBorder}`,
            background: "transparent",
            cursor: "pointer",
            font: "12px 'JetBrains Mono',monospace",
            color: t.textBody,
            padding: "6px 12px",
            borderRadius: 4,
          }}
        >
          $ reset
        </button>
      </div>

      <div ref={scrollRef} onScroll={handleScroll} style={{ flex: 1, overflowY: "auto", padding: "26px 22px" }}>
        <div style={{ maxWidth: 640, margin: "0 auto", display: "flex", flexDirection: "column", gap: 18 }}>
          {messages.map((m) =>
            m.role === "user" ? (
              <div
                key={m.id}
                style={{
                  alignSelf: "flex-end",
                  maxWidth: "80%",
                  font: "13.5px 'JetBrains Mono',monospace",
                  color: t.bubbleText,
                  background: t.bubbleBg,
                  borderRadius: 4,
                  padding: "9px 14px",
                }}
              >
                {m.text}
              </div>
            ) : (
              <div key={m.id} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {m.text && (
                  <div className="relay-markdown" style={{ color: t.textBody }}>
                    <Streamdown>{m.text}</Streamdown>
                  </div>
                )}
                {m.component && <ComponentCard t={t} sessionId={sessionId} payload={m.component} />}
              </div>
            ),
          )}
          {isTyping && <TypingIndicator t={t} />}
        </div>
      </div>

      <form
        onSubmit={onSubmit}
        style={{ padding: "16px 22px", borderTop: `1px solid ${t.ruleColor}`, background: t.panelBg }}
      >
        <div style={{ maxWidth: 640, margin: "0 auto", display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ color: t.accent, font: "13px 'JetBrains Mono',monospace" }}>&gt;</span>
          <input
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            placeholder="type a command…"
            style={{
              flex: 1,
              border: "none",
              outline: "none",
              background: "transparent",
              font: "13.5px 'JetBrains Mono',monospace",
              color: t.textPrimary,
            }}
          />
          <button
            type="submit"
            style={{
              border: "none",
              cursor: "pointer",
              background: t.accent,
              color: t.panelBg,
              font: "600 12px 'JetBrains Mono',monospace",
              padding: "8px 14px",
              borderRadius: 4,
            }}
          >
            send
          </button>
        </div>
      </form>
    </div>
  );
}

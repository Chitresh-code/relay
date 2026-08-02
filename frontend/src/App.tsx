import type { FormEvent } from "react";
import { useState } from "react";
import { streamChat } from "./api";
import { ChatView } from "./components/ChatView";
import { Landing } from "./components/Landing";
import { getSessionId, newSessionId } from "./session";
import { darkTheme, lightTheme } from "./theme";
import type { ChatMessage, ComponentPayload } from "./types";

type View = "landing" | "chat";
type Mode = "dark" | "light";

function App() {
  const [view, setView] = useState<View>("landing");
  const [mode, setMode] = useState<Mode>("dark");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState(getSessionId);

  const t = mode === "dark" ? darkTheme : lightTheme;

  async function pushExchange(text: string) {
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", text };
    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);

    const assistantId = crypto.randomUUID();
    let assistantText = "";
    let component: ComponentPayload | undefined;
    let added = false;

    const addOrUpdate = (patch: Partial<ChatMessage>) => {
      if (!added) {
        added = true;
        setIsTyping(false);
        setMessages((prev) => [...prev, { id: assistantId, role: "assistant", text: "", ...patch }]);
      } else {
        setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, ...patch } : m)));
      }
    };

    for await (const event of streamChat(sessionId, text)) {
      if (event.type === "token") {
        assistantText += event.text;
        addOrUpdate({ text: assistantText });
      } else if (event.type === "component") {
        component = { tool: event.tool, content: event.content };
        addOrUpdate({ component });
      } else if (event.type === "error") {
        addOrUpdate({ text: assistantText || `⚠ ${event.message}` });
      }
    }
    setIsTyping(false);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    setInput("");
    setView("chat");
    pushExchange(text);
  }

  function handlePrompt(text: string) {
    setView("chat");
    pushExchange(text);
  }

  function handleReset() {
    setSessionId(newSessionId());
    setMessages([]);
    setInput("");
    setView("landing");
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: t.outerBg,
        fontFamily: "system-ui,-apple-system,sans-serif",
        position: "relative",
        transition: "background .2s",
      }}
    >
      <div
        style={{
          position: "fixed",
          top: 18,
          right: 20,
          zIndex: 20,
          display: "flex",
          gap: 6,
          border: `1px solid ${t.panelBorder}`,
          borderRadius: 999,
          padding: 3,
          background: t.panelBg,
        }}
      >
        <button
          onClick={() => setMode("light")}
          style={{
            border: "none",
            cursor: "pointer",
            font: "600 11px system-ui,sans-serif",
            padding: "5px 12px",
            borderRadius: 999,
            background: mode === "dark" ? "transparent" : "oklch(20% 0.01 90)",
            color: mode === "dark" ? "oklch(60% 0.01 90)" : "#fff",
          }}
        >
          Light
        </button>
        <button
          onClick={() => setMode("dark")}
          style={{
            border: "none",
            cursor: "pointer",
            font: "600 11px system-ui,sans-serif",
            padding: "5px 12px",
            borderRadius: 999,
            background: mode === "dark" ? "oklch(20% 0.01 90)" : "transparent",
            color: mode === "dark" ? "#fff" : "oklch(30% 0.01 90)",
          }}
        >
          Dark
        </button>
      </div>

      {view === "landing" ? (
        <Landing t={t} input={input} onInputChange={setInput} onSubmit={handleSubmit} onPrompt={handlePrompt} />
      ) : (
        <ChatView
          t={t}
          messages={messages}
          isTyping={isTyping}
          input={input}
          onInputChange={setInput}
          onSubmit={handleSubmit}
          onReset={handleReset}
        />
      )}
    </div>
  );
}

export default App;

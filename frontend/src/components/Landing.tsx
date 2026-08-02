import type { FormEvent } from "react";
import type { Theme } from "../theme";

const prompts = [
  { label: "skills --list", text: "What are your strongest skills?" },
  { label: "projects --recent", text: "Show me your recent projects" },
  { label: "experience --list", text: "Walk me through your work experience" },
  { label: "contact --info", text: "How can I reach you?" },
];

export function Landing({
  t,
  input,
  onInputChange,
  onSubmit,
  onPrompt,
}: {
  t: Theme;
  input: string;
  onInputChange: (v: string) => void;
  onSubmit: (e: FormEvent) => void;
  onPrompt: (text: string) => void;
}) {
  return (
    <div
      style={{
        maxWidth: 640,
        margin: "0 auto",
        padding: "90px 24px 60px",
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        boxSizing: "border-box",
      }}
    >
      <div style={{ font: "12px 'JetBrains Mono',monospace", color: t.accent }}>// relay.chitresh</div>
      <div style={{ font: "700 44px/1.15 system-ui,sans-serif", color: t.textPrimary, marginTop: 18 }}>
        Chitresh Gyanani
      </div>
      <div style={{ font: "14px 'JetBrains Mono',monospace", color: t.accent, marginTop: 8 }}>
        solution_architect · applied_ai_ml · backend
      </div>
      <p style={{ font: "15px/1.65 system-ui,sans-serif", color: t.textBody, margin: "20px 0 0", maxWidth: 480 }}>
        Two years shipping enterprise AI into production for clients including UKG and Autodesk — RAG
        platforms, agent orchestration, containerized APIs, owned end to end. Ask me anything, I'll
        answer from the real resume.
      </p>

      <form onSubmit={onSubmit} style={{ marginTop: 40 }}>
        <div
          style={{
            background: t.inputBg,
            border: `1px solid ${t.inputBorder}`,
            borderRadius: 6,
            padding: "14px 16px",
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <span style={{ font: "13px 'JetBrains Mono',monospace", color: t.accent }}>&gt;</span>
          <input
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            placeholder="ask anything about my work"
            style={{
              flex: 1,
              border: "none",
              outline: "none",
              background: "transparent",
              font: "14px 'JetBrains Mono',monospace",
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
            run
          </button>
        </div>
      </form>

      <div style={{ marginTop: 18, display: "flex", flexDirection: "column", gap: 2 }}>
        {prompts.map((p) => (
          <button
            key={p.label}
            onClick={() => onPrompt(p.text)}
            style={{
              all: "unset",
              cursor: "pointer",
              font: "13px 'JetBrains Mono',monospace",
              color: t.textBody,
              padding: "9px 4px",
              borderBottom: `1px solid ${t.ruleColor}`,
            }}
          >
            <span style={{ color: t.accent }}>$</span>&nbsp; {p.label}
          </button>
        ))}
      </div>

      <div
        style={{
          marginTop: "auto",
          paddingTop: 40,
          font: "12px 'JetBrains Mono',monospace",
          color: t.textMuted,
          display: "flex",
          gap: 14,
          flexWrap: "wrap",
        }}
      >
        <span>new_delhi_in</span>
        <span>·</span>
        <span>gychitresh1290@gmail.com</span>
        <span>·</span>
        <span>linkedin.com/in/chitresh-gyanani</span>
      </div>
    </div>
  );
}

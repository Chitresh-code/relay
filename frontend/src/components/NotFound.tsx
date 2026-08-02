import type { Theme } from "../theme";

export function NotFound({ t, path }: { t: Theme; path: string }) {
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
      <div style={{ font: "700 64px/1.15 system-ui,sans-serif", color: t.textPrimary, marginTop: 18 }}>404</div>
      <div style={{ font: "14px 'JetBrains Mono',monospace", color: t.accent, marginTop: 8 }}>
        route_not_found
      </div>
      <p style={{ font: "15px/1.65 system-ui,sans-serif", color: t.textBody, margin: "20px 0 0", maxWidth: 480 }}>
        <span style={{ font: "13px 'JetBrains Mono',monospace", color: t.textMuted }}>{path}</span> isn't a page
        here — this is a single chat endpoint, not a multi-route site.
      </p>

      <a
        href="/"
        style={{
          alignSelf: "flex-start",
          marginTop: 32,
          border: `1px solid ${t.panelBorder}`,
          background: "transparent",
          color: t.textBody,
          cursor: "pointer",
          font: "600 12px 'JetBrains Mono',monospace",
          padding: "8px 14px",
          borderRadius: 4,
          textDecoration: "none",
        }}
      >
        $ cd ~
      </a>
    </div>
  );
}

import { useState } from "react";
import type { Theme } from "../theme";
import type {
  ComponentPayload,
  ContactItem,
  EducationItem,
  ExperienceItem,
  ProjectItem,
  RequestContactCard,
  ResumeCard,
  SkillGroup,
} from "../types";

const tagStyle = (t: Theme, small = false) => ({
  font: `${small ? 11 : 12}px 'JetBrains Mono',monospace`,
  color: t.tagText,
  border: `1px solid ${t.tagBorder}`,
  borderRadius: 3,
  padding: small ? "4px 9px" : "5px 10px",
});

const cardStyle = (t: Theme) => ({
  border: `1px solid ${t.cardBorder}`,
  borderRadius: 6,
  padding: "16px 18px",
});

function SkillsCard({ t, groups }: { t: Theme; groups: SkillGroup[] }) {
  return (
    <div style={{ ...cardStyle(t), display: "flex", flexDirection: "column", gap: 12 }}>
      {groups.map((g) => (
        <div key={g.category}>
          <div
            style={{
              font: "11px 'JetBrains Mono',monospace",
              letterSpacing: ".1em",
              color: t.accent,
              textTransform: "uppercase",
              marginBottom: 8,
            }}
          >
            {g.category}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {g.skills.map((s) => (
              <span key={s} style={tagStyle(t)}>
                {s}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ProjectsCard({ t, items }: { t: Theme; items: ProjectItem[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {items.map((p) => (
        <div key={p.title} style={cardStyle(t)}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <div style={{ font: "600 15px system-ui,sans-serif", color: t.textPrimary }}>{p.title}</div>
            <div style={{ font: "11px 'JetBrains Mono',monospace", color: t.textMuted }}>{p.year}</div>
          </div>
          <div style={{ font: "13px/1.55 system-ui,sans-serif", color: t.textBody, marginTop: 6 }}>
            {p.description}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
            {p.tech.map((tc) => (
              <span key={tc} style={tagStyle(t, true)}>
                {tc}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ExperienceCard({ t, items }: { t: Theme; items: ExperienceItem[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {items.map((e) => (
        <div key={e.role + e.company} style={cardStyle(t)}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <div style={{ font: "600 14.5px system-ui,sans-serif", color: t.textPrimary }}>{e.role}</div>
            <div style={{ font: "11px 'JetBrains Mono',monospace", color: t.textMuted }}>{e.period}</div>
          </div>
          <div style={{ font: "12.5px system-ui,sans-serif", color: t.textMuted, marginTop: 2 }}>
            {e.company}
          </div>
          <ul
            style={{
              margin: "10px 0 0",
              paddingLeft: 18,
              font: "13px/1.55 system-ui,sans-serif",
              color: t.textBody,
            }}
          >
            {e.bullets.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function EducationCard({ t, items }: { t: Theme; items: EducationItem[] }) {
  return (
    <div style={{ ...cardStyle(t), display: "flex", flexDirection: "column", gap: 12 }}>
      {items.map((e) => (
        <div key={e.degree}>
          <div style={{ font: "600 13.5px system-ui,sans-serif", color: t.textPrimary }}>{e.degree}</div>
          <div style={{ font: "12.5px system-ui,sans-serif", color: t.textMuted, marginTop: 2 }}>
            {e.school} · {e.period}
          </div>
        </div>
      ))}
    </div>
  );
}

function ContactCard({ t, items }: { t: Theme; items: ContactItem[] }) {
  return (
    <div style={{ ...cardStyle(t), display: "flex", flexDirection: "column", gap: 9 }}>
      {items.map((c) => (
        <div
          key={c.label}
          style={{ display: "flex", justifyContent: "space-between", font: "12.5px 'JetBrains Mono',monospace" }}
        >
          <span style={{ color: t.textMuted }}>{c.label}</span>
          <span style={{ color: t.textPrimary }}>{c.value}</span>
        </div>
      ))}
    </div>
  );
}

function ResumeCardView({ t, resume }: { t: Theme; resume: ResumeCard }) {
  return (
    <div style={{ ...cardStyle(t), display: "flex", alignItems: "center", gap: 14 }}>
      <div
        style={{
          width: 40,
          height: 40,
          borderRadius: 6,
          background: t.inputBg,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flex: "none",
          border: `1px solid ${t.inputBorder}`,
        }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={t.accent} strokeWidth={2}>
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
          <path d="M14 2v6h6" />
        </svg>
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ font: "600 13.5px system-ui,sans-serif", color: t.textPrimary }}>{resume.name} — Resume</div>
        <div style={{ font: "11.5px 'JetBrains Mono',monospace", color: t.textMuted, marginTop: 2 }}>
          {resume.format} · updated {resume.updated} · {resume.size}
        </div>
      </div>
      <a
        href={resume.url ?? "#"}
        target="_blank"
        rel="noreferrer"
        style={{
          border: `1px solid ${t.accent}`,
          background: "transparent",
          color: t.accent,
          cursor: "pointer",
          font: "600 12px 'JetBrains Mono',monospace",
          padding: "8px 14px",
          borderRadius: 4,
          textDecoration: "none",
        }}
      >
        download
      </a>
    </div>
  );
}

function InfoCardView({ t, quote }: { t: Theme; quote: string }) {
  return (
    <div style={cardStyle(t)}>
      <div
        style={{
          font: "11px 'JetBrains Mono',monospace",
          letterSpacing: ".1em",
          color: t.accent,
          textTransform: "uppercase",
          marginBottom: 8,
        }}
      >
        about
      </div>
      <div style={{ font: "13.5px/1.6 system-ui,sans-serif", color: t.textBody }}>{quote}</div>
    </div>
  );
}

// ponytail: submission just acks locally for now — wiring this to the escalate()/Telegram
// flow is Phase 2 (ARCHITECTURE.md §3 request_contact, ROADMAP.md Phase 2).
function RequestContactCardView({ t, reason }: { t: Theme; reason: string }) {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  if (submitted) {
    return (
      <div style={cardStyle(t)}>
        <div style={{ font: "13.5px system-ui,sans-serif", color: t.textBody }}>
          Thanks — Chitresh will follow up{email ? ` at ${email}` : ""}.
        </div>
      </div>
    );
  }

  return (
    <div style={{ ...cardStyle(t), display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ font: "13px system-ui,sans-serif", color: t.textBody }}>{reason}</div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setSubmitted(true);
        }}
        style={{ display: "flex", gap: 8 }}
      >
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@company.com (optional)"
          style={{
            flex: 1,
            border: `1px solid ${t.inputBorder}`,
            background: t.inputBg,
            borderRadius: 4,
            padding: "8px 10px",
            font: "12.5px 'JetBrains Mono',monospace",
            color: t.textPrimary,
            outline: "none",
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
      </form>
    </div>
  );
}

export function ComponentCard({ t, payload }: { t: Theme; payload: ComponentPayload }) {
  switch (payload.tool) {
    case "show_skills":
      return <SkillsCard t={t} groups={payload.content.groups} />;
    case "show_projects":
      return <ProjectsCard t={t} items={payload.content.items} />;
    case "show_experience":
      return <ExperienceCard t={t} items={payload.content.items} />;
    case "show_education":
      return <EducationCard t={t} items={payload.content.items} />;
    case "show_contact":
      return <ContactCard t={t} items={payload.content.items} />;
    case "show_resume":
      return <ResumeCardView t={t} resume={payload.content as ResumeCard} />;
    case "show_info":
      return <InfoCardView t={t} quote={payload.content.quote} />;
    case "request_contact":
      return <RequestContactCardView t={t} reason={(payload.content as RequestContactCard).reason} />;
    default:
      return null;
  }
}

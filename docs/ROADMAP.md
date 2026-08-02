# Build Roadmap

Status: Draft v1 · companion to [[PRD.md]] / [[ARCHITECTURE.md]]

Phased so each phase ships something usable rather than one big-bang build.

## Phase 0 — Content prep (no code)
- Curated bio/FAQ doc (the LinkedIn substitute — see PRD §6).
- Finalize resume source text to feed the agent (the LaTeX resume in `../resume` can be the base).
- Register the Telegram bot handle (e.g. `@relayhq_bot`) via @BotFather and grab an OpenRouter API key.

## Phase 1 — Core agent, no UI polish
- FastAPI backend + Agents SDK pointed at OpenRouter (free model), knowledge base wired in as plain context (no DB yet).
- `/chat` endpoint, structured `ChatResponse` output.
- Minimal SPA: single input + rendered `text`/`list`/`cards`/`link` components.
- Deploy: FastAPI Cloud + Vercel, both free tier.

## Phase 2 — Escalation + Telegram admin bot
- `escalate()` tool + `contact_form` component.
- Telegram bot (webhook), escalation alerts, `/stats`.
- Neon Postgres: conversations, messages, escalations, leads tables.
- Resend integration for reply-to-recruiter emails.

## Phase 3 — Governance & ops
- Rate limiting (Upstash Redis).
- Retention purge job + privacy notice on the widget.
- `usage_stats` logging + weekly digest (`/weekly`, GitHub Actions cron for the Monday push).

## Phase 4 — Polish
- GitHub connector (cached public repo/pinned summary).
- Better card/list rendering, loading states, mobile pass.
- Point the subdomain at the deployed frontend, final DNS.

Not planned unless the need shows up later: vector DB/RAG, dedicated LLM observability platform,
separate admin web dashboard (see ARCHITECTURE §4/§5 and PRD §6 for the specific upgrade paths).

# Build Roadmap

Status: Draft v1 · companion to [[PRD.md]] / [[ARCHITECTURE.md]]

This isn't a fixture/PoC — it's a real system being built toward production, just not built in the
original phase order below (streaming, GitHub integration, and the Telegram notes/RAG layer shipped
before escalation and the Postgres data model did, because they were the more valuable/requested
pieces at the time). This doc tracks actual status so it doesn't drift from the code again.

## Shipped

- FastAPI backend + Agents SDK via OpenRouter (OpenAI-compatible env vars, swappable provider).
- `/chat` SSE endpoint: streamed text + tool-triggered UI cards (skills, experience, education,
  contact, resume, live GitHub projects). See [[ARCHITECTURE.md]] §3.
- Vite + React + TypeScript SPA, deferred component rendering, sticky-bottom scroll during streaming.
- Resume view/download card, backed by the real file (never model-generated).
- Live GitHub projects card (5 most recent public repos, 1hr cache, README-summary fallback for repos
  with no description).
- Configurability: `content/profile.md`, `content/system_prompt.md`, resume PDF, and a handful of env
  vars are the only person-specific inputs — no hardcoded personal defaults in app code.
- Admin Telegram bot (long-polling, single-`chat_id` auth): conversational note-taking, LLM rewrite +
  confirm/cancel flow.
- `search_context` RAG tool over admin notes: Neon Postgres (`DATABASE_URL`) + OpenAI-compatible
  embeddings, brute-force cosine (small corpus, no vector index needed yet). See [[ARCHITECTURE.md]]
  §6.
- GitHub branch protection on `main` (PR required, no force-push/deletion) — makes the "never commit
  to main directly" rule in CLAUDE.md enforced, not just convention.
- CI: `.github/workflows/ci.yml` runs backend tests + frontend typecheck/build on every PR, both
  required as status checks on the `main` branch protection rule. See [[ARCHITECTURE.md]] §13.
- Escalation handoff: submitting `request_contact` calls `POST /contact`, which alerts the admin on
  Telegram with an LLM-generated summary of what the recruiter wants (`summarize_for_admin` in
  `app/agent.py`, falls back to the raw escalation reason on any failure) and, if an email was
  given, sends the recruiter an immediate Resend receipt (HTML template in
  `content/email_receipt.html`, same swap-the-file pattern as the profile/prompt). Forwarding the
  admin's Telegram reply back to the recruiter is still planned — see below.
- Rate limiting: `POST /chat` and `POST /contact` capped per client IP over any REST-compatible
  Redis (fails open if unconfigured or on Redis errors). See [[ARCHITECTURE.md]] §9.

## Planned — roughly in build order

### Data model + sessions (Neon)
- `conversations`, `messages`, `escalations`, `leads`, `usage_stats` tables (same Neon project the
  notes table already lives in — no new database). See [[ARCHITECTURE.md]] §8.
- Move `app/main.py`'s in-memory `_sessions` dict onto `messages` — required before this can run on
  serverless hosting without losing conversation history between requests.

### Escalation
- Forward the admin's Telegram reply back to the recruiter's email via Resend — the remaining piece
  of the escalation loop (alert + receipt are shipped, see above).

### Governance & ops
- Retention purge job via `pg_cron` directly in Neon (pure SQL, no external scheduler needed) +
  privacy notice on the widget. See [[ARCHITECTURE.md]] §12.
- `usage_stats` logging + weekly digest, pushed automatically every Monday via GitHub Actions cron
  hitting an internal endpoint (needs an outbound Telegram call, so it can't be `pg_cron`-only).
- Telegram bot slash commands: `/health`, `/stats`, `/weekly`. See [[ARCHITECTURE.md]] §14.

### Deploy
- FastAPI Cloud (backend) + Vercel (frontend), both free tier.
- Point a personal subdomain at the deployed frontend, final DNS.

Not planned unless the need shows up later: RAG over the *core* knowledge base (resume/bio — the
small notes-specific RAG layer above is a different thing, see PRD §6), dedicated LLM observability
platform, separate admin web dashboard (see [[ARCHITECTURE.md]] §7/§9 and [[PRD.md]] §6 for the
specific upgrade paths).

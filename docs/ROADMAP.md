# Build Roadmap

Status: Draft v1 · companion to [[PRD.md]] / [[ARCHITECTURE.md]]

This isn't a fixture/PoC — it's a real system being built toward production, just not built in the
original phase order below (streaming, GitHub integration, and the Telegram notes/RAG layer shipped
before escalation and the Postgres data model did, because they were the more valuable/requested
pieces at the time). This doc tracks actual status so it doesn't drift from the code again.

## Shipped

- FastAPI backend + Strands Agents via OpenRouter (OpenAI-compatible env vars, swappable provider).
- `/chat` SSE endpoint: streamed text + tool-triggered UI cards (skills, experience, education,
  contact, resume, live GitHub projects). See [[ARCHITECTURE.md]] §3.
- Vite + React + TypeScript SPA, deferred component rendering, sticky-bottom scroll during streaming.
- Resume view/download card, backed by the real file (never model-generated).
- Live GitHub projects card (5 most recent public repos, 1hr cache, README-summary fallback for repos
  with no description).
- Configurability: `content/profile.md`, `content/system_prompt.md`, resume PDF, and a handful of env
  vars are the only person-specific inputs — no hardcoded personal defaults in app code.
- Admin Telegram bot (long-polling, single-`chat_id` auth), with a private admin agent
  (`app/admin_agent.py`) the admin chats with directly: `save_note` (notes for the public agent),
  `get_session_history` (pull a recruiter transcript by `session_id`), `send_email` (draft/send
  outreach emails, resume attached). Replaced the old fixed rewrite/confirm/cancel flow with a
  real conversation. See [[ARCHITECTURE.md]] §6.
- `search_context` RAG tool over admin notes: Neon Postgres (`DATABASE_URL`) + OpenAI-compatible
  embeddings, brute-force cosine (small corpus, no vector index needed yet). See [[ARCHITECTURE.md]]
  §6.
- GitHub branch protection on `main` (PR required, no force-push/deletion) — makes the "never commit
  to main directly" rule in CLAUDE.md enforced, not just convention.
- CI: `.github/workflows/ci.yml` runs backend tests + frontend typecheck/build on every PR, both
  required as status checks on the `main` branch protection rule. See [[ARCHITECTURE.md]] §13.
- Escalation handoff, full loop: submitting `request_contact` (now collecting name + email) calls
  `POST /contact`, which alerts the admin on Telegram with an LLM-generated summary of what the
  recruiter wants (`summarize_for_admin` in `app/agent.py`, falls back to the raw escalation
  reason on any failure) and, if an email was given, sends the recruiter an immediate receipt via
  Resend — personally worded and signed, resume PDF attached (`content/email_receipt.html`, same
  swap-the-file pattern as the profile/prompt). Replying to that Telegram alert forwards the
  admin's actual reply to the recruiter's email (also resume-attached, `content/email_reply.html`)
  — the message-to-lead mapping lives in `leads.telegram_message_id`, see
  `app/telegram_bot.py:poll`/`app/sessions.py:get_lead_by_message_id`.
- Rate limiting: `POST /chat` and `POST /contact` capped per client IP over any REST-compatible
  Redis (fails open if unconfigured or on Redis errors). See [[ARCHITECTURE.md]] §9.
- Data model + sessions (Neon): `conversations`, `messages`, `escalations`, `leads` tables, one
  shared pool (`app/db.py`). `app/main.py`'s in-memory `_sessions` dict is gone — history now lives
  in `app/sessions.py`, backed by Postgres with an in-memory-per-process fallback when
  `DATABASE_URL` is unset (local dev). `/contact` now records an `escalations` row per submission
  and a `leads` row when an email is given. See [[ARCHITECTURE.md]] §4/§8.
- Retention purge job via GitHub Actions cron (`.github/workflows/retention-purge.yml`, daily)
  hitting `POST /internal/retention-purge` (`app/sessions.py:purge_old_messages`) + a privacy
  notice line on the chat widget. Originally planned as a `pg_cron` job, but `CREATE EXTENSION`/
  `cron.schedule` need a privileged Neon role not every `DATABASE_URL` grants — same GitHub
  Actions + internal-endpoint mechanism as the weekly digest below instead. See
  [[ARCHITECTURE.md]] §12.
- `usage_stats` table (`app/usage_stats.py`) + logging from both agents, weekly digest pushed
  automatically every Monday via GitHub Actions cron (`.github/workflows/weekly-digest.yml`)
  hitting `POST /internal/weekly-digest`. See [[ARCHITECTURE.md]] §7/§8/§12.
- Telegram bot slash commands: `/health`, `/stats`, `/weekly` (shares its digest builder with the
  Monday auto-push above). See [[ARCHITECTURE.md]] §14.
- Themed 404 page for any URL path other than `/` (the SPA has no router, so this checks
  `window.location.pathname` directly — `frontend/src/components/NotFound.tsx`).
- Agent orchestration migrated from the OpenAI Agents SDK to **Strands Agents**
  (`app/agent.py`, `app/admin_agent.py`, `app/usage_stats.py`) — same OpenRouter model, same tool
  set and streaming UX, model-agnostic runtime instead of OpenAI's own agent framework. See
  [[ARCHITECTURE.md]] §2.
- **Deployed.** Backend on FastAPI Cloud (`https://relay.fastapicloud.dev`, app `relay`), frontend
  on Vercel (`https://relay-ten-rho.vercel.app`, project `relay`), both free tier, live at the
  final public URL `https://relay.chitreshgyanani.com` (CNAME `relay` → `cname.vercel-dns.com`).
  `ALLOWED_ORIGINS` is scoped to just the custom domain. `RELAY_BASE_URL`/`RELAY_INTERNAL_API_KEY`
  GitHub Actions secrets set and both cron workflows (`weekly-digest.yml`, `retention-purge.yml`)
  verified working against the live backend.
- Admin Telegram agent's chat history now persists to Postgres (`telegram_bot._handle_message`,
  same `conversations`/`messages` tables as recruiter sessions, under a synthetic `admin:{chat_id}`
  `session_id`) instead of an in-memory-per-process dict that reset on every backend restart. See
  [[ARCHITECTURE.md]] §6.
- Response-quality pass on the public agent's free-text replies (the ones outside the predefined
  UI-tool paths) — added guidance to `content/system_prompt.md` so pure-conversation turns (a bare
  greeting, opinion questions like fit/weaknesses/pitch) answer naturally and concretely instead of
  reading like a canned bot line, and added a manual regression harness
  (`backend/scripts/eval_agent_quality.py`, `uv run python -m scripts.eval_agent_quality`) to
  spot-check that after future prompt/model changes — not part of CI since it makes real, billed
  LLM calls.

## Planned — roughly in build order

Not planned unless the need shows up later: RAG over the *core* knowledge base (resume/bio — the
small notes-specific RAG layer above is a different thing, see PRD §6), dedicated LLM observability
platform, separate admin web dashboard (see [[ARCHITECTURE.md]] §7/§9 and [[PRD.md]] §6 for the
specific upgrade paths).

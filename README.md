# Relay

A chat agent grounded in a resume/profile, with streaming replies, rich UI cards (skills,
experience, education, live GitHub projects, resume download), and escalation to Telegram
when it can't answer. Runs on free-tier infra end to end (OpenRouter, FastAPI Cloud, Vercel).

Docs: [PRD](docs/PRD.md) · [Architecture](docs/ARCHITECTURE.md) · [Roadmap](docs/ROADMAP.md) ·
repo conventions: [CLAUDE.md](CLAUDE.md)

## Quickstart

```
make install   # backend (uv) + frontend (npm) deps
make run       # both dev servers together, http://localhost:5173
```

Backend needs a `.env` in `backend/` (copy `backend/.env.example`) — at minimum an
`OPENAI_API_KEY` for whichever OpenAI-compatible provider you point `OPENAI_BASE_URL` at
(defaults to OpenRouter's free tier).

Other useful targets: `make backend`, `make frontend`, `make test`, `make build`.

## Structure

- `backend/` — FastAPI + OpenAI Agents SDK, `/chat` SSE endpoint
- `frontend/` — Vite + React + TypeScript SPA

## Making it yours

Relay is deliberately not hardcoded to one person. To point it at a different profile:

1. Replace `backend/content/profile.md` (resume/bio text) and, optionally, the resume PDF at
   `backend/content/<file>.pdf` (update `RESUME_FILE` in `.env` to match).
2. Edit `backend/content/system_prompt.md` if you want different tool-calling behavior.
3. Set `CANDIDATE_NAME`, `AGENT_NAME`, and `GITHUB_USERNAME` in `backend/.env` — see
   `backend/.env.example` for the full list of config env vars.

No code changes needed for a rebrand — see [ARCHITECTURE.md §6](docs/ARCHITECTURE.md) for
the full configurability rundown.

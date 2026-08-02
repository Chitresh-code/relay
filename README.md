# Relay

A chat agent grounded in Chitresh Gyanani's resume/profile, with escalation to
Telegram when it can't answer. Lives at `relay.chitreshgyanani.com`.

Docs: [PRD](docs/PRD.md) · [Architecture](docs/ARCHITECTURE.md) · [Roadmap](docs/ROADMAP.md)

## Structure

- `backend/` — FastAPI + OpenAI Agents SDK (via OpenRouter free models)
- `frontend/` — Vite + React SPA

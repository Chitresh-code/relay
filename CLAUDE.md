# CLAUDE.md

Instructions for Claude (and any contributor) working in this repo.

## Project

Relay — a chat agent grounded in Chitresh Gyanani's resume/profile, with escalation to
Telegram when it can't answer. See [PRD](docs/PRD.md), [Architecture](docs/ARCHITECTURE.md),
[Roadmap](docs/ROADMAP.md) before making architectural changes — keep them in sync with
the code as it evolves.

- `backend/` — FastAPI + OpenAI Agents SDK (via OpenRouter free models)
- `frontend/` — Vite + React + TypeScript SPA

## Python tooling

Use **uv**, not `pip`/`venv` directly.

- Add a dependency: `uv add <package>` (no pinned version unless there's a specific reason
  to pin — let uv resolve the latest compatible version).
- Remove a dependency: `uv remove <package>`.
- Run things inside the project env: `uv run <command>`.
- Target **Python 3.14** for this project.

## Git workflow

- **Never commit directly to `main`.** Always work on a branch.
- Branch naming: `type/short-title` — e.g. `feat/chat-endpoint`, `fix/sse-parsing`,
  `chore/repo-setup`, `docs/update-prd`.
- Merge via pull request (`gh pr create`), not direct pushes to `main`.
- Commit subjects use **Conventional Commits**: `type(scope): summary` — one line, no
  filler body unless something non-obvious needs explaining. Types: `feat`, `fix`, `docs`,
  `chore`, `refactor`, `test`, `ci`.

## Conventions

- Keep changes minimal and scoped — no speculative abstractions, no unused config knobs.
- Docs (`docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`) are the source of truth
  for product/architecture decisions; update them when a decision changes, don't let them
  drift from the code.

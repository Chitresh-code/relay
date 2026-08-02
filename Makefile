.PHONY: install install-backend install-frontend backend frontend run test build

install: install-backend install-frontend

run:
	$(MAKE) -j2 backend frontend

install-backend:
	cd backend && uv sync

install-frontend:
	cd frontend && npm install

backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && uv run python -m tests.test_smoke && uv run python -m tests.test_context_store

build:
	cd frontend && npm run build

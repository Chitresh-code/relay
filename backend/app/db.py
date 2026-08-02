import asyncio
import os

import asyncpg

# Neon Postgres, shared pool across every *_store module — one pool, not one per module (Neon
# caps concurrent connections). Unset -> get_pool() returns None; callers fall back to whatever
# graceful-disable behavior fits them (see context_store.py, sessions.py).
DATABASE_URL = os.environ.get("DATABASE_URL", "")

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id SERIAL PRIMARY KEY, text TEXT NOT NULL,
    embedding DOUBLE PRECISION[] NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY, session_id TEXT NOT NULL UNIQUE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_message_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL, content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS messages_conversation_idx ON messages(conversation_id, id);
CREATE TABLE IF NOT EXISTS escalations (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    reason TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    escalation_id INTEGER NOT NULL REFERENCES escalations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    telegram_message_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now());
-- CREATE TABLE IF NOT EXISTS above is a no-op on a table that already exists (even if it
-- predates these columns) — ALTER ... ADD COLUMN IF NOT EXISTS is what actually keeps an
-- existing `leads` table in Neon current with this schema.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS name TEXT NOT NULL DEFAULT '';
ALTER TABLE leads ADD COLUMN IF NOT EXISTS telegram_message_id INTEGER;
CREATE TABLE IF NOT EXISTS usage_stats (
    date DATE PRIMARY KEY,
    requests INTEGER NOT NULL DEFAULT 0,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0);
"""

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def get_pool() -> asyncpg.Pool | None:
    global _pool
    if not DATABASE_URL:
        return None
    if _pool is None:
        async with _pool_lock:
            if _pool is None:  # re-check: another task may have created it while we waited
                _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)
                async with _pool.acquire() as conn:
                    await conn.execute(SCHEMA)
    return _pool

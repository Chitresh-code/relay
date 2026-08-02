"""Conversation history + escalation/lead persistence — the Postgres side of app/main.py's
session and /contact handling. Same DATABASE_URL as context_store.py (shared pool, app/db.py)."""

import logging

from .db import get_pool

logger = logging.getLogger("relay.sessions")

# ponytail: in-memory fallback when DATABASE_URL is unset — same graceful-disable pattern as
# mailer/rate_limit/context_store, so local dev without Postgres still keeps chat history within
# a process. Lost on restart and not shared across workers; that's exactly the gap Postgres closes.
_memory: dict[str, list[dict[str, str]]] = {}


async def get_history(session_id: str) -> list[dict[str, str]]:
    pool = await get_pool()
    if pool is None:
        return list(_memory.get(session_id, []))
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT m.role, m.content FROM messages m "
            "JOIN conversations c ON c.id = m.conversation_id "
            "WHERE c.session_id = $1 ORDER BY m.id",
            session_id,
        )
    return [{"role": r["role"], "content": r["content"]} for r in rows]


async def append_message(session_id: str, role: str, content: str) -> None:
    pool = await get_pool()
    if pool is None:
        _memory.setdefault(session_id, []).append({"role": role, "content": content})
        return
    async with pool.acquire() as conn:
        async with conn.transaction():
            conv_id = await conn.fetchval(
                "INSERT INTO conversations (session_id) VALUES ($1) "
                "ON CONFLICT (session_id) DO UPDATE SET last_message_at = now() "
                "RETURNING id",
                session_id,
            )
            await conn.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES ($1, $2, $3)",
                conv_id, role, content,
            )


async def record_escalation(session_id: str, reason: str) -> int | None:
    """Logs every /contact submission, with or without an email — needed to tell escalations
    that became usable leads apart from dead-end ones (PRD §7 success metric). No-op (returns
    None) when Postgres isn't configured; the Telegram alert itself never depends on this."""
    pool = await get_pool()
    if pool is None:
        return None
    async with pool.acquire() as conn:
        async with conn.transaction():
            conv_id = await conn.fetchval(
                "INSERT INTO conversations (session_id) VALUES ($1) "
                "ON CONFLICT (session_id) DO UPDATE SET last_message_at = now() "
                "RETURNING id",
                session_id,
            )
            return await conn.fetchval(
                "INSERT INTO escalations (conversation_id, reason) VALUES ($1, $2) RETURNING id",
                conv_id, reason,
            )


async def record_lead(escalation_id: int | None, email: str) -> None:
    if escalation_id is None:
        return
    pool = await get_pool()
    if pool is None:
        return
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO leads (escalation_id, email) VALUES ($1, $2)", escalation_id, email
        )

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


async def record_lead(
    escalation_id: int | None, email: str, name: str = "", telegram_message_id: int | None = None
) -> None:
    if escalation_id is None:
        return
    pool = await get_pool()
    if pool is None:
        return
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO leads (escalation_id, email, name, telegram_message_id) VALUES ($1, $2, $3, $4)",
            escalation_id, email, name, telegram_message_id,
        )


async def purge_old_messages(days: int = 90) -> int:
    """Retention purge (PRD §4/ARCHITECTURE §12): deletes transcripts older than `days`.
    Triggered by GitHub Actions (POST /internal/retention-purge), not pg_cron — pg_cron needs a
    privileged Neon role not every DATABASE_URL grants. escalations/leads are untouched (they're
    leads, not transcripts). No-op (returns 0) when Postgres isn't configured."""
    pool = await get_pool()
    if pool is None:
        return 0
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM messages WHERE created_at < now() - make_interval(days => $1)", days
        )
    return int(result.split()[-1])


async def get_recent_user_messages(days: int, limit: int = 150) -> list[str]:
    """Recruiter questions from the trailing `days` — feeds the weekly digest's LLM topic
    summary (app/agent.py:summarize_weekly_topics). Empty list, not an error, when Postgres
    isn't configured."""
    pool = await get_pool()
    if pool is None:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT content FROM messages WHERE role = 'user' "
            "AND created_at >= now() - make_interval(days => $1) "
            "ORDER BY created_at DESC LIMIT $2",
            days, limit,
        )
    return [r["content"] for r in rows]


async def get_period_counts(days: int) -> dict[str, int]:
    """Conversation/escalation/lead counts over the trailing `days`, for the weekly digest's
    recap line."""
    pool = await get_pool()
    if pool is None:
        return {"conversations": 0, "escalations": 0, "leads": 0}
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT "
            "(SELECT COUNT(*) FROM conversations WHERE started_at >= now() - make_interval(days => $1)) AS conversations, "
            "(SELECT COUNT(*) FROM escalations WHERE created_at >= now() - make_interval(days => $1)) AS escalations, "
            "(SELECT COUNT(*) FROM leads WHERE created_at >= now() - make_interval(days => $1)) AS leads",
            days,
        )
    return dict(row)


async def get_lead_by_message_id(message_id: int) -> dict[str, str] | None:
    """Looks up the recruiter's name/email from the Telegram message_id of the escalation alert
    the admin is replying to — how the bot knows where to forward that reply (see
    telegram_bot.py). ponytail: no in-memory fallback — reply-forwarding is simply unavailable
    without Postgres, same as everything else in this module when DATABASE_URL is unset."""
    pool = await get_pool()
    if pool is None:
        return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT name, email FROM leads WHERE telegram_message_id = $1", message_id
        )
    return {"name": row["name"], "email": row["email"]} if row else None

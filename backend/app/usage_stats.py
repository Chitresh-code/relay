"""Aggregate LLM usage tracking (requests/tokens/cost) — one row per day in Postgres, upserted
after every agent run, backing the /stats and /weekly Telegram commands (app/telegram_bot.py)
and the weekly digest. No-op (recording silently skipped, reads return zeros) when DATABASE_URL
is unset, same graceful-disable pattern as the rest of the *_store modules."""

import os
from datetime import date, timedelta

from .db import get_pool

COST_PER_1M_INPUT = float(os.environ.get("OPENAI_COST_PER_1M_INPUT_TOKENS", "0"))
COST_PER_1M_OUTPUT = float(os.environ.get("OPENAI_COST_PER_1M_OUTPUT_TOKENS", "0"))


async def record_usage(usage: dict, requests: int) -> None:
    """`usage` is a Strands EventLoopMetrics.accumulated_usage dict (inputTokens/outputTokens,
    Bedrock-style camelCase since Strands models its types after the Bedrock API); `requests` is
    the event loop cycle count (one model call per cycle) — Strands has no single field for it."""
    if not requests:
        return
    pool = await get_pool()
    if pool is None:
        return
    input_tokens = usage.get("inputTokens", 0)
    output_tokens = usage.get("outputTokens", 0)
    cost = (input_tokens / 1_000_000) * COST_PER_1M_INPUT + (output_tokens / 1_000_000) * COST_PER_1M_OUTPUT
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO usage_stats (date, requests, tokens_in, tokens_out, estimated_cost_usd) "
            "VALUES (CURRENT_DATE, $1, $2, $3, $4) "
            "ON CONFLICT (date) DO UPDATE SET "
            "requests = usage_stats.requests + EXCLUDED.requests, "
            "tokens_in = usage_stats.tokens_in + EXCLUDED.tokens_in, "
            "tokens_out = usage_stats.tokens_out + EXCLUDED.tokens_out, "
            "estimated_cost_usd = usage_stats.estimated_cost_usd + EXCLUDED.estimated_cost_usd",
            requests, input_tokens, output_tokens, cost,
        )


async def get_range_stats(days: int) -> dict:
    """Aggregate requests/tokens/cost over the trailing `days` (inclusive of today), plus a live
    distinct-session count over the same window. ponytail: unique sessions isn't a separate
    incrementally-updated column — a COUNT(DISTINCT) against `conversations`/`messages` is cheap
    enough at personal-scale traffic and can't drift out of sync with the real data."""
    empty = {"requests": 0, "tokens_in": 0, "tokens_out": 0, "estimated_cost_usd": 0.0, "unique_sessions": 0}
    pool = await get_pool()
    if pool is None:
        return empty
    since = date.today() - timedelta(days=days - 1)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COALESCE(SUM(requests),0) requests, COALESCE(SUM(tokens_in),0) tokens_in, "
            "COALESCE(SUM(tokens_out),0) tokens_out, COALESCE(SUM(estimated_cost_usd),0) estimated_cost_usd "
            "FROM usage_stats WHERE date >= $1",
            since,
        )
        sessions = await conn.fetchval(
            "SELECT COUNT(DISTINCT c.session_id) FROM conversations c "
            "JOIN messages m ON m.conversation_id = c.id WHERE m.created_at >= $1",
            since,
        )
    return {**dict(row), "unique_sessions": sessions or 0}

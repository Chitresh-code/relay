import logging
from collections.abc import Awaitable, Callable

from .db import get_pool as _get_pool

logger = logging.getLogger("relay.context_store")

# Neon Postgres, not SQLite — FastAPI Cloud/Vercel are serverless, so a local file wouldn't
# persist (or be shared) across instances. Unset -> notes are silently dropped/empty instead
# of crashing, same graceful-disable pattern as the Telegram bot when its token is unset.
EmbedFn = Callable[[str], Awaitable[list[float]]]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


async def add_note(text: str, embed: EmbedFn) -> None:
    pool = await _get_pool()
    if pool is None:
        logger.warning("DATABASE_URL not set — dropping note instead of saving it: %.60s", text)
        return
    vector = await embed(text)
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO notes (text, embedding) VALUES ($1, $2)", text, vector)


async def search_notes(query: str, embed: EmbedFn, top_k: int = 3, threshold: float = 0.3) -> list[str]:
    """ponytail: brute-force cosine scan in Python — fine at hundreds of rows; move to
    pgvector's <=> operator (Neon supports the extension) if the notes table ever gets large."""
    pool = await _get_pool()
    if pool is None:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT text, embedding FROM notes")
    if not rows:
        return []
    query_vector = await embed(query)
    scored = [(row["text"], _cosine(query_vector, row["embedding"])) for row in rows]
    scored.sort(key=lambda r: r[1], reverse=True)
    return [text for text, score in scored[:top_k] if score >= threshold]

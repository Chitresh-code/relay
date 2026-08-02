import sqlite3
import struct
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path

# ponytail: SQLite file, not Postgres/Mongo — this is a personal note store (dozens to low
# hundreds of short entries), not a multi-writer service. Swap if that ever changes.
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "context.db"
DB_PATH.parent.mkdir(exist_ok=True)

EmbedFn = Callable[[str], Awaitable[list[float]]]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS notes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, "
        "embedding BLOB NOT NULL, created_at TEXT NOT NULL)"
    )
    return conn


def _pack(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


def _unpack(blob: bytes) -> list[float]:
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


async def add_note(text: str, embed: EmbedFn) -> None:
    vector = await embed(text)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO notes (text, embedding, created_at) VALUES (?, ?, ?)",
            (text, _pack(vector), datetime.now(timezone.utc).isoformat()),
        )


async def search_notes(query: str, embed: EmbedFn, top_k: int = 3, threshold: float = 0.3) -> list[str]:
    """ponytail: brute-force cosine scan in Python — fine at hundreds of rows; swap for
    sqlite-vec/pgvector if the notes table ever gets large."""
    with _connect() as conn:
        rows = conn.execute("SELECT text, embedding FROM notes").fetchall()
    if not rows:
        return []
    query_vector = await embed(query)
    scored = [(text, _cosine(query_vector, _unpack(blob))) for text, blob in rows]
    scored.sort(key=lambda r: r[1], reverse=True)
    return [text for text, score in scored[:top_k] if score >= threshold]

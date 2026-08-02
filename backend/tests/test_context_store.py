"""Plain assert-based smoke checks — no framework, no API key needed. Run: python -m tests.test_context_store"""

import asyncio

from app import context_store


async def _fake_embed(text: str) -> list[float]:
    # deterministic toy embedding: word-presence vector over a tiny fixed vocabulary
    vocab = ["kubernetes", "python", "cooking", "guitar"]
    return [1.0 if w in text.lower() else 0.0 for w in vocab]


async def _run() -> None:
    context_store.DB_PATH.unlink(missing_ok=True)

    await context_store.add_note("Comfortable running Kubernetes in production.", embed=_fake_embed)
    await context_store.add_note("Enjoys cooking on weekends.", embed=_fake_embed)

    results = await context_store.search_notes("kubernetes experience", embed=_fake_embed, top_k=1)
    assert results == ["Comfortable running Kubernetes in production."], results

    empty = await context_store.search_notes("guitar", embed=_fake_embed, top_k=1)
    assert empty == [], empty

    context_store.DB_PATH.unlink(missing_ok=True)


def test_add_and_search_notes() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    test_add_and_search_notes()
    print("ok")

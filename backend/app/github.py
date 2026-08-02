import os
import time
from collections.abc import Awaitable, Callable

import httpx

GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "")
_CACHE_TTL_SECONDS = 3600  # ponytail: process-local cache, resets on redeploy — fine at this traffic
_cache: dict[str, tuple[float, list[dict]]] = {}

DescribeFn = Callable[[str], Awaitable[str]]


async def _fetch_readme(client: httpx.AsyncClient, owner: str, repo: str) -> str:
    resp = await client.get(
        f"https://api.github.com/repos/{owner}/{repo}/readme",
        headers={"Accept": "application/vnd.github.raw"},
    )
    return resp.text if resp.status_code == 200 else ""


async def fetch_recent_repos(limit: int = 5, describe: DescribeFn | None = None) -> list[dict]:
    """Recent public, non-fork repos. When a repo has no description and `describe` is given,
    fills it in from the README (e.g. an LLM summary) — cached alongside the rest so it's only
    generated once per TTL window, not on every chat request."""
    if not GITHUB_USERNAME:
        return []

    cached = _cache.get(GITHUB_USERNAME)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"https://api.github.com/users/{GITHUB_USERNAME}/repos",
            params={"sort": "pushed", "direction": "desc", "per_page": limit + 5, "type": "owner"},
            headers={"Accept": "application/vnd.github+json"},
        )
        resp.raise_for_status()
        repos = [r for r in resp.json() if not r.get("fork")][:limit]

        items = []
        for r in repos:
            description = r.get("description") or ""
            if not description and describe is not None:
                readme = await _fetch_readme(client, GITHUB_USERNAME, r["name"])
                if readme:
                    try:
                        description = await describe(readme[:1500])
                    except Exception:
                        description = ""
            items.append(
                {
                    "name": r["name"],
                    "description": description,
                    "url": r["html_url"],
                    "language": r.get("language") or "",
                    "updated": (r.get("pushed_at") or "")[:10],
                }
            )

    _cache[GITHUB_USERNAME] = (time.time(), items)
    return items

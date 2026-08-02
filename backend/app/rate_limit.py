import logging
import os

import httpx
from fastapi import Request

logger = logging.getLogger("relay.rate_limit")

REDIS_URL = os.environ.get("REDIS_REST_URL", "").rstrip("/")
REDIS_TOKEN = os.environ.get("REDIS_REST_TOKEN", "")

PER_MINUTE_LIMIT = 20
PER_DAY_LIMIT = 200


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_rate_limit(ip: str) -> bool:
    """True if the request is allowed. No-ops (always allows) when Redis isn't configured,
    and fails open on Redis errors — a rate limiter shouldn't be able to take the app down."""
    if not REDIS_URL or not REDIS_TOKEN:
        return True
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            resp = await client.post(
                f"{REDIS_URL}/pipeline",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                json=[
                    ["SET", f"rl:m:{ip}", "0", "EX", "60", "NX"],
                    ["INCR", f"rl:m:{ip}"],
                    ["SET", f"rl:d:{ip}", "0", "EX", "86400", "NX"],
                    ["INCR", f"rl:d:{ip}"],
                ],
            )
            resp.raise_for_status()
        except httpx.HTTPError:
            logger.exception("Redis rate-limit check failed — failing open")
            return True
        results = resp.json()
        minute_count, day_count = results[1]["result"], results[3]["result"]
        return minute_count <= PER_MINUTE_LIMIT and day_count <= PER_DAY_LIMIT

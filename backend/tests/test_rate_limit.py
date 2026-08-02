"""Plain assert-based checks — no network, no Redis needed. Run: python -m tests.test_rate_limit"""

import asyncio

from app import rate_limit


def test_allows_when_unconfigured():
    rate_limit.REDIS_URL = ""
    rate_limit.REDIS_TOKEN = ""
    assert asyncio.run(rate_limit.check_rate_limit("1.2.3.4")) is True


def test_client_ip_prefers_forwarded_header():
    class FakeRequest:
        headers = {"x-forwarded-for": "9.9.9.9, 5.5.5.5"}
        client = None

    assert rate_limit.client_ip(FakeRequest()) == "9.9.9.9"


if __name__ == "__main__":
    test_allows_when_unconfigured()
    test_client_ip_prefers_forwarded_header()
    print("ok")

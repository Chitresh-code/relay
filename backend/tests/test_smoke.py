"""Plain assert-based smoke checks — no framework, no API key needed. Run: python -m tests.test_smoke"""

from app.knowledge import PROFILE
from app.main import sse


def test_profile_loaded():
    assert "Chitresh Gyanani" in PROFILE
    assert len(PROFILE) > 200


def test_sse_format():
    out = sse("token", {"text": "hi"})
    assert out == 'event: token\ndata: {"text": "hi"}\n\n'


if __name__ == "__main__":
    test_profile_loaded()
    test_sse_format()
    print("ok")

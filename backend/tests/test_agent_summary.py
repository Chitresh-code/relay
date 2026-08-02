"""Plain assert-based checks — no network needed. Run: python -m tests.test_agent_summary"""

import asyncio

from app import agent


def test_no_history_returns_reason_unchanged():
    result = asyncio.run(agent.summarize_for_admin([], "wants to talk about a role"))
    assert result == "wants to talk about a role"


def test_falls_back_to_reason_on_llm_failure():
    async def boom(**kwargs):
        raise RuntimeError("simulated failure")

    original = agent._client.chat.completions.create
    agent._client.chat.completions.create = boom
    try:
        history = [{"role": "user", "content": "hi"}]
        result = asyncio.run(agent.summarize_for_admin(history, "fallback reason"))
    finally:
        agent._client.chat.completions.create = original
    assert result == "fallback reason"


if __name__ == "__main__":
    test_no_history_returns_reason_unchanged()
    test_falls_back_to_reason_on_llm_failure()
    print("ok")

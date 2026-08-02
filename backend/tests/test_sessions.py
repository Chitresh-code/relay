"""Plain assert-based checks — no DB needed. Run: python -m tests.test_sessions"""

import asyncio

from app import sessions


def test_history_round_trips_in_memory_when_unconfigured():
    sessions._memory.clear()
    asyncio.run(sessions.append_message("s1", "user", "hi"))
    asyncio.run(sessions.append_message("s1", "assistant", "hello"))
    assert asyncio.run(sessions.get_history("s1")) == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


def test_record_escalation_and_lead_are_noops_when_unconfigured():
    escalation_id = asyncio.run(sessions.record_escalation("s1", "wants a role"))
    assert escalation_id is None
    asyncio.run(sessions.record_lead(escalation_id, "a@b.com"))  # must not raise


if __name__ == "__main__":
    test_history_round_trips_in_memory_when_unconfigured()
    test_record_escalation_and_lead_are_noops_when_unconfigured()
    print("ok")

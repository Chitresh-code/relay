"""Plain assert-based smoke checks — no network, no API key needed. Run: python -m tests.test_admin_agent"""

from app import admin_agent


def test_agent_has_expected_tools():
    assert set(admin_agent.admin_agent.tool_names) == {"save_note", "get_session_history", "send_email"}


def test_instructions_mention_candidate_name():
    assert admin_agent.CANDIDATE_NAME in admin_agent.INSTRUCTIONS


if __name__ == "__main__":
    test_agent_has_expected_tools()
    test_instructions_mention_candidate_name()
    print("ok")

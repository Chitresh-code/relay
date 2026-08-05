import logging

from openai import RateLimitError
from strands import Agent, tool

from .agent import AGENT_NAME, MODEL, _embed, _to_strands_messages
from .context_store import add_note
from .knowledge import CANDIDATE_NAME
from .mailer import send_custom_email
from .sessions import get_history
from .usage_stats import record_usage

logger = logging.getLogger("relay.admin_agent")


@tool
async def save_note(text: str) -> str:
    """Save a note for the public-facing agent to retrieve later via search_context — role
    changes, new projects, availability, anything that should ground future recruiter answers."""
    await add_note(text, embed=_embed)
    return "Saved."


@tool
async def get_session_history(session_id: str) -> str:
    """Look up the full chat transcript for a recruiter session_id — the id included in every
    escalation alert. Use this to understand the full context before replying or summarizing."""
    history = await get_history(session_id)
    if not history:
        return "No history found for that session."
    return "\n".join(f"{m['role']}: {m['content']}" for m in history)


@tool
async def send_email(to: str, subject: str, body: str) -> str:
    """Send an email on the admin's behalf — outreach, follow-ups, anything. The resume PDF is
    attached automatically. Only call this once the admin has clearly confirmed it should go out."""
    await send_custom_email(to, subject, body)
    return f"Sent to {to}."


INSTRUCTIONS = (
    f"You're {CANDIDATE_NAME}'s private assistant for {AGENT_NAME}, talking with them directly "
    "over Telegram (this chat is admin-only, already authenticated). Help them:\n"
    "- Save notes for the public-facing agent (save_note) — rewrite rough input into a clean, "
    "factual note first if needed, keep every fact, don't invent anything.\n"
    "- Look up a recruiter's full conversation and summarize it (get_session_history) — useful "
    "when handling an escalation.\n"
    "- Draft and send outreach/follow-up emails (send_email) — draft the text in chat first and "
    "only send once they've clearly said to.\n"
    "Be concise, this is a chat, not a report."
)

admin_agent = Agent(
    name=f"{AGENT_NAME} Admin",
    system_prompt=INSTRUCTIONS,
    model=MODEL,
    tools=[save_note, get_session_history, send_email],
    callback_handler=None,
)


async def run_admin_agent(history: list[dict[str, str]]) -> str:
    try:
        result = await admin_agent.invoke_async(_to_strands_messages(history))
        await record_usage(result.metrics.accumulated_usage, len(result.metrics.cycle_durations))
        return str(result)
    except RateLimitError:
        logger.warning("Model rate limit hit")
        return "Hit the model rate limit — give it a bit and try again."
    except Exception:
        logger.exception("Admin agent run failed")
        return "Something went wrong processing that — try again?"

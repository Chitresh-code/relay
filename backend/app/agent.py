import logging
import os

from openai import AsyncOpenAI, RateLimitError
from pydantic import BaseModel
from strands import Agent, tool
from strands.models.openai import OpenAIModel
from strands.models.openai_responses import OpenAIResponsesModel

from .context_store import search_notes
from .github import fetch_recent_repos
from .knowledge import PROFILE, RESUME_INFO, SYSTEM_PROMPT_TEMPLATE
from .usage_stats import record_usage

# Standard OpenAI SDK env var names, kept generic on purpose: swapping providers (OpenRouter
# free tier now, straight OpenAI or anything else OpenAI-compatible later) is just an env var
# change, no code change. Defaults point at OpenRouter's free tier.
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
MODEL_NAME = os.environ.get("OPENAI_RESPONSES_MODEL", "openrouter/free")
AGENT_NAME = os.environ.get("AGENT_NAME", "Relay")
# OpenRouter doesn't host its own free embedding model — this defaults to an OpenAI model
# behind the same OPENAI_BASE_URL/OPENAI_API_KEY, so point those at a provider that serves it
# (or override this) if you're staying on OpenRouter's free chat tier for everything else.
EMBED_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "openai/text-embedding-3-small")
# gpt-5/o-series reasoning models only support reasoning_effort above "none" together with
# function tools on the Responses API (/v1/responses) — Chat Completions has no way to carry
# reasoning state across a tool round-trip, so it rejects anything but "none" once tools are
# attached. OPENAI_API_STYLE picks which endpoint Strands talks to; defaults to chat_completions
# since that's what OpenRouter (and most non-OpenAI-official endpoints) serve.
REASONING_EFFORT = os.environ.get("OPENAI_REASONING_EFFORT", "")
API_STYLE = os.environ.get("OPENAI_API_STYLE", "chat_completions")

logger = logging.getLogger("relay.agent")

_client = AsyncOpenAI(base_url=BASE_URL, api_key=os.environ["OPENAI_API_KEY"])

# reasoning_effort is a top-level Chat Completions param but a nested {"reasoning": {"effort":
# ...}} object on the Responses API — same setting, different body shape per endpoint.
_params = None
if REASONING_EFFORT:
    _params = (
        {"reasoning": {"effort": REASONING_EFFORT}}
        if API_STYLE == "responses"
        else {"reasoning_effort": REASONING_EFFORT}
    )

_ModelClass = OpenAIResponsesModel if API_STYLE == "responses" else OpenAIModel
# client_args (not client=): OpenAIResponsesModel only accepts client_args, so this stays
# portable across both model classes at the cost of a second AsyncOpenAI client under the hood.
MODEL = _ModelClass(model_id=MODEL_NAME, client_args={"base_url": BASE_URL, "api_key": os.environ["OPENAI_API_KEY"]}, params=_params)


async def _describe_from_readme(readme_text: str) -> str:
    """One-off summarization call (not the tool-calling agent) for repos GitHub gave no description."""
    resp = await _client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "Summarize this GitHub repo README in one concise sentence (max 25 words) "
                "describing what the project does. Reply with only the sentence.",
            },
            {"role": "user", "content": readme_text},
        ],
        max_completion_tokens=60,
    )
    return (resp.choices[0].message.content or "").strip()


async def _embed(text: str) -> list[float]:
    resp = await _client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


async def summarize_for_admin(history: list[dict[str, str]], reason: str) -> str:
    """One-off call briefing the admin on an escalation: what the recruiter actually wants,
    not the raw transcript. Falls back to the agent's own escalation reason on any failure —
    this is a convenience on top of the alert, not something that should ever block it."""
    if not history:
        return reason
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    try:
        resp = await _client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You're briefing the profile owner on an incoming recruiter escalation. "
                    "In 2-3 sentences: what role/opportunity (if mentioned), what they're actually "
                    "asking, and why it needed a human. Be concrete, no filler, no greeting.",
                },
                {"role": "user", "content": f"Escalation reason: {reason}\n\nConversation:\n{transcript}"},
            ],
            max_completion_tokens=150,
        )
        return (resp.choices[0].message.content or reason).strip()
    except RateLimitError:
        logger.warning("Model rate limit hit — falling back to raw reason")
        return reason
    except Exception:
        logger.exception("Admin summary generation failed — falling back to raw reason")
        return reason


async def summarize_weekly_topics(messages: list[str]) -> str:
    """One-off call for the weekly digest (app/telegram_bot.py): turns a sample of the week's
    recruiter questions into 3-5 recurring topics. Falls back to a plain notice on any failure —
    a nice-to-have on top of the numeric stats, not something that should block the digest."""
    if not messages:
        return "No conversations this week."
    sample = "\n".join(f"- {m}" for m in messages[:150])
    try:
        resp = await _client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "These are recruiter questions asked to a resume chatbot this week. "
                    "In 3-5 short bullet points, name the recurring topics/themes. No filler.",
                },
                {"role": "user", "content": sample},
            ],
            max_completion_tokens=150,
        )
        return (resp.choices[0].message.content or "").strip()
    except RateLimitError:
        logger.warning("Model rate limit hit — skipping weekly topic summary")
        return "(topic summary unavailable — rate limited)"
    except Exception:
        logger.exception("Weekly topic summary generation failed")
        return "(topic summary unavailable)"


UI_TOOL_NAMES = {
    "show_skills",
    "show_projects",
    "show_experience",
    "show_education",
    "show_contact",
    "show_resume",
    "show_info",
    "request_contact",
}


class SkillGroup(BaseModel):
    category: str
    skills: list[str]


class ExperienceItem(BaseModel):
    role: str
    company: str
    period: str
    bullets: list[str]


class EducationItem(BaseModel):
    degree: str
    school: str
    period: str


class ContactItem(BaseModel):
    label: str
    value: str


@tool
def show_skills(groups: list[SkillGroup]) -> str:
    """Render grouped skill tags."""
    return "Shown."


@tool
def show_projects() -> str:
    """Render project cards: the 5 most recently updated public GitHub repos, fetched live."""
    return "Shown."


@tool
def show_experience(items: list[ExperienceItem]) -> str:
    """Render role cards."""
    return "Shown."


@tool
def show_education(items: list[EducationItem]) -> str:
    """Render education cards."""
    return "Shown."


@tool
def show_contact(items: list[ContactItem]) -> str:
    """Render key/value contact rows."""
    return "Shown."


@tool
def show_resume() -> str:
    """Render the resume view/download card. Call when the user asks for the resume, CV, or a download."""
    return "Shown."


@tool
def show_info(quote: str) -> str:
    """Render a pull-quote card."""
    return "Shown."


@tool
def request_contact(reason: str) -> str:
    """Render an inline contact-capture form when a question needs the profile owner directly."""
    return "Requested."


@tool
async def search_context(query: str) -> str:
    """Look up notes added via the admin Telegram bot — info newer than the static profile
    (role changes, new projects, availability). Not a UI tool: nothing is shown to the
    recruiter for this call, it only feeds you more information before you answer."""
    notes = await search_notes(query, embed=_embed)
    return "\n".join(f"- {n}" for n in notes) if notes else "No additional notes found."


SYSTEM_PROMPT = SYSTEM_PROMPT_TEMPLATE.replace("{agent_name}", AGENT_NAME).replace("{profile}", PROFILE)

agent = Agent(
    name=AGENT_NAME,
    system_prompt=SYSTEM_PROMPT,
    model=MODEL,
    tools=[
        show_skills,
        show_projects,
        show_experience,
        show_education,
        show_contact,
        show_resume,
        show_info,
        request_contact,
        search_context,
    ],
    callback_handler=None,
)


def _to_strands_messages(history: list[dict[str, str]]) -> list[dict]:
    """DB-stored history is plain {role, content} text turns our own app wrote (app/sessions.py)
    — never model/tool-call blocks — so converting to Strands' {role, content: [{"text": ...}]}
    shape here can't smuggle in a forged toolUse block. See Strands' trusted-message-history docs."""
    return [{"role": m["role"], "content": [{"text": m["content"]}]} for m in history]


async def stream_reply(history: list[dict[str, str]]):
    """Yields ("token" | "component" | "error", payload) tuples for the SSE layer."""
    emitted_tools: set[str] = set()
    result = None
    try:
        async for event in agent.stream_async(_to_strands_messages(history)):
            if "data" in event:
                yield "token", {"text": event["data"]}
            elif "message" in event:
                message = event["message"]
                if message.get("role") != "assistant":
                    continue
                for block in message.get("content", []):
                    tool_use = block.get("toolUse")
                    if not tool_use:
                        continue
                    name = tool_use.get("name")
                    # Enforce "at most one UI tool call per turn" server-side too — small/free
                    # models don't always follow that instruction, and repeat calls would mean
                    # redundant GitHub/README/LLM work for show_projects.
                    if name in emitted_tools:
                        continue
                    if name is not None:
                        emitted_tools.add(name)
                    if name == "show_resume":
                        # Real file metadata/URL, never left to the model to invent.
                        yield "component", {"tool": name, "content": RESUME_INFO}
                    elif name == "show_projects":
                        # Live GitHub data, not model-generated — repo names/links must be real.
                        try:
                            items = await fetch_recent_repos(describe=_describe_from_readme)
                        except Exception:
                            items = []
                        yield "component", {"tool": name, "content": {"items": items}}
                    elif name in UI_TOOL_NAMES:
                        yield "component", {"tool": name, "content": tool_use.get("input") or {}}
            elif "result" in event:
                result = event["result"]
        if result is not None:
            await record_usage(result.metrics.accumulated_usage, len(result.metrics.cycle_durations))
    except RateLimitError:
        logger.warning("Model rate limit hit")
        yield "error", {"message": "Getting a lot of requests right now — try again in a minute."}
    except Exception as exc:  # model hiccups, etc. — surface, don't crash
        logger.exception("stream_reply failed")
        yield "error", {"message": str(exc)}

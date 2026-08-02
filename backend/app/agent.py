import json
import os

from agents import Agent, Runner, function_tool, set_tracing_disabled
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from pydantic import BaseModel

from .context_store import search_notes
from .github import fetch_recent_repos
from .knowledge import PROFILE, RESUME_INFO, SYSTEM_PROMPT_TEMPLATE

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

_client = AsyncOpenAI(base_url=BASE_URL, api_key=os.environ["OPENAI_API_KEY"])
set_tracing_disabled(True)  # tracing uploads to platform.openai.com — not relevant off-OpenAI

# Built directly against our client (not agents.Agent(model=<string>)): the SDK's default
# MultiProvider splits bare model strings on "/" as a provider prefix, which misreads
# OpenRouter ids like "meta-llama/llama-3.3-70b-instruct:free" as prefix "meta-llama".
MODEL = OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=_client)


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
        max_tokens=60,
    )
    return (resp.choices[0].message.content or "").strip()


async def _embed(text: str) -> list[float]:
    resp = await _client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


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


@function_tool
def show_skills(groups: list[SkillGroup]) -> str:
    """Render grouped skill tags."""
    return "Shown."


@function_tool
def show_projects() -> str:
    """Render project cards: the 5 most recently updated public GitHub repos, fetched live."""
    return "Shown."


@function_tool
def show_experience(items: list[ExperienceItem]) -> str:
    """Render role cards."""
    return "Shown."


@function_tool
def show_education(items: list[EducationItem]) -> str:
    """Render education cards."""
    return "Shown."


@function_tool
def show_contact(items: list[ContactItem]) -> str:
    """Render key/value contact rows."""
    return "Shown."


@function_tool
def show_resume() -> str:
    """Render the resume view/download card. Call when the user asks for the resume, CV, or a download."""
    return "Shown."


@function_tool
def show_info(quote: str) -> str:
    """Render a pull-quote card."""
    return "Shown."


@function_tool
def request_contact(reason: str) -> str:
    """Render an inline contact-capture form when a question needs the profile owner directly."""
    return "Requested."


@function_tool
async def search_context(query: str) -> str:
    """Look up notes added via the admin Telegram bot — info newer than the static profile
    (role changes, new projects, availability). Not a UI tool: nothing is shown to the
    recruiter for this call, it only feeds you more information before you answer."""
    notes = await search_notes(query, embed=_embed)
    return "\n".join(f"- {n}" for n in notes) if notes else "No additional notes found."


SYSTEM_PROMPT = SYSTEM_PROMPT_TEMPLATE.replace("{agent_name}", AGENT_NAME).replace("{profile}", PROFILE)

agent = Agent(
    name=AGENT_NAME,
    instructions=SYSTEM_PROMPT,
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
)


async def stream_reply(history: list[dict[str, str]]):
    """Yields ("token" | "component" | "error", payload) tuples for the SSE layer."""
    emitted_tools: set[str] = set()
    try:
        result = Runner.run_streamed(agent, input=history)
        async for event in result.stream_events():
            if event.type == "raw_response_event":
                data = event.data
                if getattr(data, "type", None) == "response.output_text.delta":
                    yield "token", {"text": data.delta}
            elif event.type == "run_item_stream_event":
                item = event.item
                if item.type == "tool_call_item":
                    name = getattr(item.raw_item, "name", None)
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
                        try:
                            args = json.loads(item.raw_item.arguments or "{}")
                        except json.JSONDecodeError:
                            args = {}
                        yield "component", {"tool": name, "content": args}
    except Exception as exc:  # free-tier rate limits, model hiccups, etc. — surface, don't crash
        yield "error", {"message": str(exc)}

import json
import os

from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
)
from openai import AsyncOpenAI
from pydantic import BaseModel

from .knowledge import PROFILE

# Standard OpenAI SDK env var names, kept generic on purpose: swapping providers (OpenRouter
# free tier now, straight OpenAI or anything else OpenAI-compatible later) is just an env var
# change, no code change. Defaults point at OpenRouter's free tier.
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.environ.get("OPENAI_RESPONSES_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

_client = AsyncOpenAI(base_url=BASE_URL, api_key=os.environ["OPENAI_API_KEY"])
set_default_openai_client(_client)
set_default_openai_api("chat_completions")  # widest compatibility across OpenAI-compatible providers
set_tracing_disabled(True)  # tracing uploads to platform.openai.com — not relevant off-OpenAI

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


class ProjectItem(BaseModel):
    title: str
    year: str
    description: str
    tech: list[str]


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
def show_projects(items: list[ProjectItem]) -> str:
    """Render project cards."""
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
def show_resume(name: str, format: str, updated: str, size: str, url: str) -> str:
    """Render a resume download card."""
    return "Shown."


@function_tool
def show_info(quote: str) -> str:
    """Render a pull-quote card."""
    return "Shown."


@function_tool
def request_contact(reason: str) -> str:
    """Render an inline contact-capture form when a question needs Chitresh directly."""
    return "Requested."


SYSTEM_PROMPT = f"""You are Relay, an assistant answering recruiter questions about \
Chitresh Gyanani, grounded ONLY in the profile below. Never invent experience, dates, \
or claims not present here.

Call at most one UI tool per reply, and only when it genuinely helps (e.g. a list of \
projects warrants show_projects). A plain conversational answer needs no tool call.

If a question falls outside this profile, or the recruiter clearly wants to talk to \
Chitresh directly, call request_contact with a short reason instead of guessing.

--- PROFILE ---
{PROFILE}
"""

agent = Agent(
    name="Relay",
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
    ],
)


async def stream_reply(history: list[dict[str, str]]):
    """Yields ("token" | "component" | "error", payload) tuples for the SSE layer."""
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
                    if name in UI_TOOL_NAMES:
                        try:
                            args = json.loads(item.raw_item.arguments or "{}")
                        except json.JSONDecodeError:
                            args = {}
                        yield "component", {"tool": name, "content": args}
    except Exception as exc:  # free-tier rate limits, model hiccups, etc. — surface, don't crash
        yield "error", {"message": str(exc)}

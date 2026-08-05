"""Response-quality check for the public agent's free-text replies — the answers that stay
plain prose instead of triggering a UI-tool card (PRD §3.2/§3.3). Not part of the offline CI
suite (tests.test_*): this makes real, billed LLM calls against whatever model is configured.
Run manually to spot-check quality after a system-prompt or model change:

    uv run python -m scripts.eval_agent_quality

LLM output can't be hard-asserted, so this prints every Q/A pair for a human to judge, and only
auto-flags the unambiguous failure mode (empty/very short replies) — flagged or not, read the
output."""

import asyncio

from dotenv import load_dotenv

load_dotenv()  # must run before app.agent imports os.environ["OPENAI_API_KEY"]

from app.agent import stream_reply  # noqa: E402

# Recruiter-style questions expected to stay in free text — no UI tool maps to them (system
# prompt §"pure conversation"). Add a case here whenever a real conversation exposes a weak reply.
CASES = [
    "hi",
    "Are they open to contract work?",
    "What is their ideal next role?",
    "Are they open to relocating?",
    "What are their weaknesses?",
    "Give me a quick pitch on why we should hire them.",
    "Is he a good fit for a fast-paced startup?",
    "Why did they leave SSB Digital?",
]

MIN_LEN = 40  # crude non-answer detector, not a quality bar


async def run_case(question: str) -> tuple[str, list[str]]:
    text = ""
    tools: list[str] = []
    async for kind, payload in stream_reply([{"role": "user", "content": question}]):
        if kind == "token":
            text += payload["text"]
        elif kind == "component":
            tools.append(payload["tool"])
        elif kind == "error":
            text += f"[ERROR: {payload['message']}]"
    return text.strip(), tools


async def main() -> None:
    flagged = []
    for question in CASES:
        text, tools = await run_case(question)
        is_flagged = len(text) < MIN_LEN
        if is_flagged:
            flagged.append(question)
        tool_note = f" [unexpected tool call: {', '.join(tools)}]" if tools else ""
        flag_note = "  <-- FLAGGED (short/empty reply)" if is_flagged else ""
        print(f"Q: {question}{tool_note}{flag_note}\nA: {text}\n{'-' * 60}")
    print(f"\n{len(CASES)} cases, {len(flagged)} flagged.")


if __name__ == "__main__":
    asyncio.run(main())

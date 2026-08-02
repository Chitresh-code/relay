import json
import os

from dotenv import load_dotenv

load_dotenv()  # must run before .agent imports os.environ["OPENROUTER_API_KEY"]

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .agent import stream_reply

app = FastAPI(title="Relay")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("RELAY_ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["POST"],
    allow_headers=["*"],
)

# ponytail: in-memory, per-process session store — fine for one dev/single-worker deploy.
# Swap for the Postgres `messages` table (ARCHITECTURE.md §4/§8) once persistence across
# restarts/workers or the 90-day retention job matters.
_sessions: dict[str, list[dict[str, str]]] = {}
HISTORY_WINDOW = 12


class ChatRequest(BaseModel):
    session_id: str
    message: str


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/chat")
async def chat(req: ChatRequest):
    history = _sessions.setdefault(req.session_id, [])
    history.append({"role": "user", "content": req.message})

    async def gen():
        reply_text = ""
        async for event_type, payload in stream_reply(history[-HISTORY_WINDOW:]):
            if event_type == "token":
                reply_text += payload["text"]
            yield sse(event_type, payload)
        if reply_text:
            history.append({"role": "assistant", "content": reply_text})
        yield sse("done", {})

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok"}

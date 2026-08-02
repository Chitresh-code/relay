import json
import logging
import os

from dotenv import load_dotenv

load_dotenv()  # must run before .agent imports os.environ["OPENAI_API_KEY"]

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import stream_reply
from .knowledge import CONTENT_DIR

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("relay")

app = FastAPI(
    title="Relay",
    # don't expose interactive API docs in production
    docs_url="/docs" if ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if ENVIRONMENT != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["POST"],
    allow_headers=["*"],
)

# Resume PDF (and any other static content-derived assets) served straight off disk.
app.mount("/static", StaticFiles(directory=CONTENT_DIR), name="static")

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
    logger.info("chat request session=%s chars=%d", req.session_id, len(req.message))
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

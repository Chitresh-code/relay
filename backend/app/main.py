import asyncio
import contextlib
import json
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # must run before .agent imports os.environ["OPENAI_API_KEY"]

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import stream_reply, summarize_for_admin
from .knowledge import CONTENT_DIR
from .mailer import send_receipt_email
from .rate_limit import check_rate_limit, client_ip
from .telegram_bot import notify_admin
from .telegram_bot import poll as telegram_poll

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("relay")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(telegram_poll())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


app = FastAPI(
    title="Relay",
    lifespan=lifespan,
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


class ContactRequest(BaseModel):
    session_id: str
    reason: str
    email: str = ""


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/chat")
async def chat(req: ChatRequest, request: Request):
    if not await check_rate_limit(client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests — try again in a minute.")
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


@app.post("/contact")
async def contact(req: ContactRequest, request: Request):
    """Escalation handoff from the request_contact UI card: alerts the admin on Telegram and,
    if an email was left, sends the recruiter an immediate receipt via Resend."""
    if not await check_rate_limit(client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests — try again in a minute.")
    logger.info("contact request session=%s has_email=%s", req.session_id, bool(req.email))
    history = _sessions.get(req.session_id, [])
    summary = await summarize_for_admin(history, req.reason)

    lines = [f"Escalation: {summary}", f"Email: {req.email or '(not given)'}"]
    await notify_admin("\n".join(lines))

    if req.email:
        await send_receipt_email(req.email)

    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}

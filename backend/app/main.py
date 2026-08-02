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
from .sessions import append_message, get_history, record_escalation, record_lead
from .telegram_bot import build_weekly_digest, notify_admin
from .telegram_bot import poll as telegram_poll

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "")

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

HISTORY_WINDOW = 12


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ContactRequest(BaseModel):
    session_id: str
    reason: str
    name: str = ""
    email: str = ""


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/chat")
async def chat(req: ChatRequest, request: Request):
    if not await check_rate_limit(client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests — try again in a minute.")
    logger.info("chat request session=%s chars=%d", req.session_id, len(req.message))
    history = await get_history(req.session_id)
    history.append({"role": "user", "content": req.message})
    await append_message(req.session_id, "user", req.message)

    async def gen():
        reply_text = ""
        async for event_type, payload in stream_reply(history[-HISTORY_WINDOW:]):
            if event_type == "token":
                reply_text += payload["text"]
            yield sse(event_type, payload)
        if reply_text:
            await append_message(req.session_id, "assistant", reply_text)
        yield sse("done", {})

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/contact")
async def contact(req: ContactRequest, request: Request):
    """Escalation handoff from the request_contact UI card: alerts the admin on Telegram and,
    if an email was left, sends the recruiter an immediate receipt via Resend."""
    if not await check_rate_limit(client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests — try again in a minute.")
    logger.info("contact request session=%s has_email=%s", req.session_id, bool(req.email))
    history = await get_history(req.session_id)
    summary = await summarize_for_admin(history, req.reason)

    lines = [
        f"Escalation: {summary}",
        f"Session: {req.session_id}",
        f"Name: {req.name or '(not given)'}",
        f"Email: {req.email or '(not given)'}",
    ]
    if req.email:
        lines.append("(Reply to this message to respond — it'll be emailed to them.)")
    message_id = await notify_admin("\n".join(lines))

    escalation_id = await record_escalation(req.session_id, req.reason)
    if req.email:
        await record_lead(escalation_id, req.email, name=req.name, telegram_message_id=message_id)
        await send_receipt_email(req.email, req.name)

    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/internal/weekly-digest")
async def internal_weekly_digest(request: Request):
    """Hit by the GitHub Actions cron (.github/workflows/weekly-digest.yml) every Monday to push
    the digest without waiting for someone to ask via /weekly. 404s (not 401) when unconfigured,
    so the endpoint is invisible rather than just unauthorized — same graceful-disable pattern as
    the rest of the app's optional features."""
    if not INTERNAL_API_KEY or request.headers.get("X-Internal-Key") != INTERNAL_API_KEY:
        raise HTTPException(status_code=404)
    await notify_admin(await build_weekly_digest())
    return {"status": "ok"}

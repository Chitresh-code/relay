import asyncio
import logging
import os

import httpx

from .admin_agent import run_admin_agent
from .mailer import send_reply_email
from .sessions import get_lead_by_message_id

logger = logging.getLogger("relay.telegram")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

ADMIN_HISTORY_WINDOW = 20

# ponytail: single admin, single chat -> an in-memory per-process conversation is enough, no
# sessions table needed. Lost on restart; that's fine for a scratchpad chat with the admin agent.
_admin_history: dict[int, list[dict[str, str]]] = {}


async def _send(client: httpx.AsyncClient, chat_id: int, text: str) -> int | None:
    resp = await client.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": text})
    return resp.json().get("result", {}).get("message_id")


async def _handle_message(client: httpx.AsyncClient, chat_id: int, text: str) -> None:
    history = _admin_history.setdefault(chat_id, [])
    history.append({"role": "user", "content": text})
    reply = await run_admin_agent(history[-ADMIN_HISTORY_WINDOW:])
    history.append({"role": "assistant", "content": reply})
    await _send(client, chat_id, reply)


async def notify_admin(text: str) -> int | None:
    """Fire-and-forget alert to the admin chat — used by the /contact escalation endpoint,
    outside the polling loop's own client. Returns the sent message_id (or None if unconfigured)
    so the caller can remember it against the lead — that's how a later reply gets forwarded."""
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        logger.info("Telegram bot not configured — skipping admin notification")
        return None
    async with httpx.AsyncClient(timeout=10) as client:
        return await _send(client, int(ADMIN_CHAT_ID), text)


async def poll() -> None:
    """Long-polls Telegram for messages from the admin chat only. A reply to an escalation alert
    is forwarded to the recruiter's email (see notify_admin/get_lead_by_message_id); anything else
    goes to the admin agent (app/admin_agent.py) — a chat that can save notes, look up a recruiter
    session's history, and draft/send outreach emails. Long-polling avoids needing a public
    webhook URL for a single-admin bot."""
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        logger.info("Telegram bot not configured (TELEGRAM_BOT_TOKEN/TELEGRAM_ADMIN_CHAT_ID unset) — skipping.")
        return

    offset = 0
    async with httpx.AsyncClient(timeout=35) as client:
        while True:
            try:
                resp = await client.get(f"{API}/getUpdates", params={"offset": offset, "timeout": 30})
                resp.raise_for_status()
                for update in resp.json().get("result", []):
                    offset = update["update_id"] + 1
                    message = update.get("message") or {}
                    chat_id = message.get("chat", {}).get("id")
                    text = message.get("text")
                    if chat_id is None or not text:
                        continue
                    if str(chat_id) != str(ADMIN_CHAT_ID):
                        logger.warning("Ignoring Telegram message from unauthorized chat_id=%s", chat_id)
                        continue

                    reply_to = message.get("reply_to_message", {}).get("message_id")
                    lead = await get_lead_by_message_id(reply_to) if reply_to else None
                    if lead:
                        await send_reply_email(lead["email"], text, lead["name"])
                        await _send(client, chat_id, f"Forwarded to {lead['email']}.")
                        continue

                    await _handle_message(client, chat_id, text)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Telegram poll loop error")
                await asyncio.sleep(5)

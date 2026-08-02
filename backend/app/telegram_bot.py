import asyncio
import logging
import os

import httpx

from .agent import MODEL_NAME, _client, _embed
from .context_store import add_note

logger = logging.getLogger("relay.telegram")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

_REWRITE_PROMPT = (
    "Rewrite the following note into a single clear, well-formed sentence or short paragraph, "
    "suitable for grounding an AI assistant that answers recruiter questions about this "
    "person. Keep every fact, don't invent anything new. Reply with only the rewritten note."
)

# ponytail: single admin, one conversation at a time -> an in-memory pending-draft dict is
# enough, no sessions table needed.
_pending: dict[int, str] = {}


async def _rewrite(raw: str) -> str:
    resp = await _client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": _REWRITE_PROMPT}, {"role": "user", "content": raw}],
        max_tokens=200,
    )
    return (resp.choices[0].message.content or raw).strip()


async def _send(client: httpx.AsyncClient, chat_id: int, text: str) -> None:
    await client.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": text})


async def _handle_message(client: httpx.AsyncClient, chat_id: int, text: str) -> None:
    pending = _pending.get(chat_id)
    lowered = text.strip().lower()

    if pending and lowered in {"save", "yes", "confirm", "ok"}:
        await add_note(pending, embed=_embed)
        del _pending[chat_id]
        await _send(client, chat_id, "Saved.")
        return

    if pending and lowered in {"cancel", "no", "discard"}:
        del _pending[chat_id]
        await _send(client, chat_id, "Discarded.")
        return

    draft = await _rewrite(text)
    _pending[chat_id] = draft
    await _send(
        client,
        chat_id,
        f'{draft}\n\n— reply "save" to confirm, send corrections to revise, or "cancel" to discard.',
    )


async def notify_admin(text: str) -> None:
    """Fire-and-forget alert to the admin chat — used by the /contact escalation endpoint,
    outside the polling loop's own client."""
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        logger.info("Telegram bot not configured — skipping admin notification")
        return
    async with httpx.AsyncClient(timeout=10) as client:
        await _send(client, int(ADMIN_CHAT_ID), text)


async def poll() -> None:
    """Long-polls Telegram for messages from the admin chat only, rewrites each one into a
    clean note via the LLM, and saves it (after confirmation) for search_context to retrieve.
    Long-polling avoids needing a public webhook URL for a single-admin bot."""
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
                    await _handle_message(client, chat_id, text)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Telegram poll loop error")
                await asyncio.sleep(5)

import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger("relay.mailer")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM_ADDRESS = os.environ.get("RESEND_FROM_ADDRESS", "")
AGENT_NAME = os.environ.get("AGENT_NAME", "Relay")

# Per-deployment template, same pattern as content/profile.md and content/system_prompt.md —
# swap the file (or the {agent_name} placeholder) without touching this module.
_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "content" / "email_receipt.html"
RECEIPT_HTML = _TEMPLATE_PATH.read_text().replace("{agent_name}", AGENT_NAME)
RECEIPT_TEXT = "Thanks for reaching out — I've received your message and will get back to you at the earliest."


async def send_receipt_email(to: str) -> None:
    """Auto-ack sent the moment a recruiter leaves an email via request_contact — confirms
    receipt and sets expectations, doesn't count as the admin's actual reply."""
    if not RESEND_API_KEY or not RESEND_FROM_ADDRESS:
        logger.info("Resend not configured (RESEND_API_KEY/RESEND_FROM_ADDRESS unset) — skipping receipt email to %s", to)
        return
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": RESEND_FROM_ADDRESS,
                "to": [to],
                "subject": "Got your message",
                "html": RECEIPT_HTML,
                "text": RECEIPT_TEXT,
            },
        )
        if resp.status_code >= 400:
            logger.error("Resend send failed status=%s body=%.200s", resp.status_code, resp.text)

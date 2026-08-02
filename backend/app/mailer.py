import base64
import html
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger("relay.mailer")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM_ADDRESS = os.environ.get("RESEND_FROM_ADDRESS", "")
# Optional: where a recruiter's reply lands if they hit "reply" in their email client instead of
# going through Telegram. Leave unset to fall back to RESEND_FROM_ADDRESS.
RESEND_REPLY_TO = os.environ.get("RESEND_REPLY_TO", "")
CANDIDATE_NAME = os.environ.get("CANDIDATE_NAME", "Your Name")
RESUME_FILE = os.environ.get("RESUME_FILE", "ChitreshGyanani.pdf")

_CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

# One shared card template (light theme, matching frontend/src/theme.ts's lightTheme) for every
# outgoing email — swap content/email_base.html to restyle without touching this module.
# {candidate_name}/{from_address} are fixed per deployment, filled once here; {body_html} is
# per-message, filled at send time in _send_email.
_BASE_TEMPLATE = (
    (_CONTENT_DIR / "email_base.html")
    .read_text()
    .replace("{candidate_name}", CANDIDATE_NAME)
    .replace("{from_address}", RESEND_FROM_ADDRESS)
)

# Every outgoing email carries the actual resume file, per deployer preference — a recruiter
# should never have to ask for it separately.
_RESUME_ATTACHMENT = {
    "filename": RESUME_FILE,
    "content": base64.b64encode((_CONTENT_DIR / RESUME_FILE).read_bytes()).decode(),
}


def _paragraphs(text: str) -> str:
    parts = [html.escape(p).replace("\n", "<br>") for p in text.strip().split("\n\n")]
    return "".join(f'<p style="margin:0 0 16px;">{p}</p>' for p in parts)


def _reply_to() -> str:
    return RESEND_REPLY_TO or RESEND_FROM_ADDRESS


async def _send_email(to: str, subject: str, body_text: str) -> None:
    if not RESEND_API_KEY or not RESEND_FROM_ADDRESS:
        logger.info("Resend not configured — skipping email to %s", to)
        return
    html_body = _BASE_TEMPLATE.replace("{body_html}", _paragraphs(body_text))
    payload = {
        "from": f"{CANDIDATE_NAME} <{RESEND_FROM_ADDRESS}>",
        "to": [to],
        "subject": subject,
        "html": html_body,
        "text": body_text,
        "attachments": [_RESUME_ATTACHMENT],
        "reply_to": [_reply_to()],
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json=payload,
        )
        if resp.status_code >= 400:
            logger.error("Resend send failed status=%s body=%.200s", resp.status_code, resp.text)


async def send_receipt_email(to: str, name: str = "") -> None:
    """Auto-ack sent the moment a recruiter leaves an email via request_contact — confirms
    receipt and sets expectations, doesn't count as the admin's actual reply."""
    greeting = name or "there"
    body = (
        f"Hi {greeting},\n\n"
        "Thanks for reaching out! I've received your message and will get back to you shortly. "
        "I've attached my resume in case it's useful in the meantime.\n\n"
        f"Best,\n{CANDIDATE_NAME}"
    )
    await _send_email(to, subject="Thanks for reaching out (my resume is attached)", body_text=body)


async def send_reply_email(to: str, reply_text: str, name: str = "") -> None:
    """The actual personal response: the admin's Telegram reply to an escalation alert,
    forwarded to the recruiter's email (see telegram_bot.py's reply-to-message handling)."""
    greeting = name or "there"
    body = f"Hi {greeting},\n\n{reply_text}\n\nBest,\n{CANDIDATE_NAME}"
    await _send_email(to, subject=f"Re: your message to {CANDIDATE_NAME} (resume attached)", body_text=body)


async def send_custom_email(to: str, subject: str, body_text: str) -> None:
    """Freeform outreach/follow-up email sent by the admin through the admin Telegram agent's
    send_email tool (see app/admin_agent.py) — resume attached automatically, same as every
    other outgoing email from this module."""
    await _send_email(to, subject=subject, body_text=body_text)

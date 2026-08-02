"""Plain assert-based checks — no network, no API key needed. Run: python -m tests.test_mailer"""

import asyncio

from app import mailer


def test_base_template_only_has_the_per_message_placeholder():
    assert "{body_html}" in mailer._BASE_TEMPLATE  # filled per-message, at send time
    assert "{candidate_name}" not in mailer._BASE_TEMPLATE  # filled once at import, footer only
    assert "{from_address}" not in mailer._BASE_TEMPLATE
    assert mailer.CANDIDATE_NAME in mailer._BASE_TEMPLATE  # footer: "Sent by X from Y"


def test_reply_to_falls_back_to_from_address_when_unset():
    mailer.RESEND_REPLY_TO = ""
    mailer.RESEND_FROM_ADDRESS = "noreply@example.com"
    assert mailer._reply_to() == "noreply@example.com"
    mailer.RESEND_REPLY_TO = "hire@example.com"
    assert mailer._reply_to() == "hire@example.com"


def test_resume_attachment_is_base64_and_named():
    assert mailer._RESUME_ATTACHMENT["filename"] == mailer.RESUME_FILE
    assert len(mailer._RESUME_ATTACHMENT["content"]) > 100


def test_paragraphs_escapes_and_preserves_breaks():
    out = mailer._paragraphs("first <b>line</b>\n\nsecond para\nwith a break")
    assert "&lt;b&gt;" in out
    assert out.count("<p") == 2
    assert "<br>" in out


def test_send_receipt_email_noop_when_unconfigured():
    mailer.RESEND_API_KEY = ""
    mailer.RESEND_FROM_ADDRESS = ""
    asyncio.run(mailer.send_receipt_email("someone@example.com", "Jamie"))  # should not raise


def test_send_reply_email_noop_when_unconfigured():
    mailer.RESEND_API_KEY = ""
    mailer.RESEND_FROM_ADDRESS = ""
    asyncio.run(mailer.send_reply_email("someone@example.com", "sure, let's talk", "Jamie"))  # should not raise


def test_send_custom_email_noop_when_unconfigured():
    mailer.RESEND_API_KEY = ""
    mailer.RESEND_FROM_ADDRESS = ""
    asyncio.run(mailer.send_custom_email("someone@example.com", "Following up", "just checking in"))


if __name__ == "__main__":
    test_base_template_only_has_the_per_message_placeholder()
    test_reply_to_falls_back_to_from_address_when_unset()
    test_resume_attachment_is_base64_and_named()
    test_paragraphs_escapes_and_preserves_breaks()
    test_send_receipt_email_noop_when_unconfigured()
    test_send_reply_email_noop_when_unconfigured()
    test_send_custom_email_noop_when_unconfigured()
    print("ok")

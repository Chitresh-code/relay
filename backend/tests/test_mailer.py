"""Plain assert-based checks — no network, no API key needed. Run: python -m tests.test_mailer"""

import asyncio

from app import mailer


def test_receipt_template_has_no_unfilled_placeholder():
    assert "{agent_name}" not in mailer.RECEIPT_HTML
    assert mailer.AGENT_NAME in mailer.RECEIPT_HTML


def test_send_receipt_email_noop_when_unconfigured():
    mailer.RESEND_API_KEY = ""
    mailer.RESEND_FROM_ADDRESS = ""
    asyncio.run(mailer.send_receipt_email("someone@example.com"))  # should not raise


if __name__ == "__main__":
    test_receipt_template_has_no_unfilled_placeholder()
    test_send_receipt_email_noop_when_unconfigured()
    print("ok")

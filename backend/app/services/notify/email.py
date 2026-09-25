"""Brevo email sending (free tier, 300/day), per Implementation_Plan.md
section 15.4. Degrades to a structured log line when BREVO_API_KEY is
missing, so invite/notification flows keep working end-to-end in dev.
"""
from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"


async def send_email(*, to_email: str, to_name: Optional[str], subject: str, html: str) -> bool:
    if not settings.BREVO_API_KEY:
        logger.warning(
            "email_not_sent_no_brevo_key",
            to=to_email,
            subject=subject,
            hint="Set BREVO_API_KEY to actually send. Logging content instead.",
        )
        logger.info("email_stub", to=to_email, subject=subject, html_preview=html[:200])
        return False

    try:
        import httpx

        payload = {
            "sender": {"email": settings.MAIL_FROM, "name": "Paytm Virasat"},
            "to": [{"email": to_email, "name": to_name or to_email}],
            "subject": subject,
            "htmlContent": html,
        }
        headers = {"api-key": settings.BREVO_API_KEY, "content-type": "application/json"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(BREVO_SEND_URL, json=payload, headers=headers)
            resp.raise_for_status()
        return True
    except Exception:
        logger.exception("email_send_failed", to=to_email)
        return False


def invite_email_html(*, role: str, vault_owner_name: str, invite_url: str) -> str:
    return f"""
    <div style="font-family:sans-serif">
      <h2>You've been invited as a {role} on Paytm Virasat</h2>
      <p>{vault_owner_name} has invited you to help protect their family's financial legacy.</p>
      <p><a href="{invite_url}">Accept your invite</a></p>
    </div>
    """

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Iterable

from app.core.config import get_settings

logger = logging.getLogger("app.email")


def send_email(subject: str, body: str, to: Iterable[str]) -> None:
    """Send a plain-text email. Logs a warning when SMTP is not configured."""
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_sender:
        logger.warning("smtp_not_configured", extra={"subject": subject, "to": list(to)})
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_sender
    msg["To"] = ", ".join(to)
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.error("smtp_send_failed", extra={"error": str(exc), "subject": subject})

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Sequence

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Raised when SMTP delivery fails after configuration looked valid."""


def _smtp_settings_ready() -> bool:
    auth_pair_valid = (settings.smtp_username is None) == (settings.smtp_password is None)
    return bool(settings.smtp_host and settings.smtp_from_address and auth_pair_valid)


def deliver_plain_email(*, to_addresses: Sequence[str], subject: str, body: str) -> None:
    """
    Deliver a plain-text email using the configured transport.

    When ``email_transport`` is ``log``, or SMTP is not fully configured,
    the message is logged at INFO (no exception).
    When ``email_transport`` is ``smtp`` and settings are complete, sends via SMTP;
    on failure, raises :class:`EmailDeliveryError` so Celery can retry.
    """
    recipients = [addr.strip() for addr in to_addresses if addr and addr.strip()]
    if not recipients:
        logger.warning("Skipping email: no valid recipients (subject=%r)", subject)
        return

    if settings.email_transport == "log" or not _smtp_settings_ready():
        if settings.email_transport == "smtp" and not _smtp_settings_ready():
            logger.warning(
                "EMAIL_TRANSPORT is smtp but SMTP settings are incomplete; "
                "logging message instead. subject=%r",
                subject,
            )
        logger.info(
            "Email (log transport): to=%s subject=%r",
            ", ".join(recipients),
            subject,
        )
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_address
    msg["To"] = ", ".join(recipients)
    msg.set_content(body, subtype="plain", charset="utf-8")

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            ) as smtp:
                if settings.smtp_username and settings.smtp_password is not None:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            ) as smtp:
                if settings.smtp_use_starttls:
                    smtp.starttls()
                if settings.smtp_username and settings.smtp_password is not None:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(msg)
    except OSError as exc:
        raise EmailDeliveryError(f"SMTP send failed: {exc}") from exc
    except smtplib.SMTPException as exc:
        raise EmailDeliveryError(f"SMTP send failed: {exc}") from exc

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from app.domains.notifications import transport
from app.domains.notifications.transport import EmailDeliveryError, deliver_plain_email


def test_deliver_plain_email_log_mode(caplog) -> None:
    transport.settings.email_transport = "log"
    with caplog.at_level("INFO", logger=transport.logger.name):
        deliver_plain_email(
            to_addresses=["a@example.com"],
            subject="Hello",
            body="Test body",
        )
    assert "a@example.com" in caplog.text
    assert "Hello" in caplog.text


def test_deliver_plain_email_smtp_sends_and_sets_headers(monkeypatch) -> None:
    monkeypatch.setattr(transport.settings, "email_transport", "smtp")
    monkeypatch.setattr(transport.settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(transport.settings, "smtp_port", 587)
    monkeypatch.setattr(transport.settings, "smtp_from_address", "from@test")
    monkeypatch.setattr(transport.settings, "smtp_username", "user")
    monkeypatch.setattr(transport.settings, "smtp_password", "pass")
    monkeypatch.setattr(transport.settings, "smtp_use_starttls", True)
    monkeypatch.setattr(transport.settings, "smtp_use_ssl", False)
    monkeypatch.setattr(transport.settings, "smtp_timeout_seconds", 5)

    mock_smtp = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = mock_smtp
    context.__exit__.return_value = None

    with patch("app.domains.notifications.transport.smtplib.SMTP", return_value=context):
        deliver_plain_email(
            to_addresses=["to@test"],
            subject="S",
            body="B",
        )

    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once_with("user", "pass")
    assert mock_smtp.send_message.call_count == 1
    sent = mock_smtp.send_message.call_args[0][0]
    assert sent["Subject"] == "S"
    assert sent["From"] == "from@test"
    assert "to@test" in sent["To"]


def test_deliver_plain_email_smtp_failure_raises(monkeypatch) -> None:
    monkeypatch.setattr(transport.settings, "email_transport", "smtp")
    monkeypatch.setattr(transport.settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(transport.settings, "smtp_from_address", "from@test")
    monkeypatch.setattr(transport.settings, "smtp_username", None)
    monkeypatch.setattr(transport.settings, "smtp_password", None)
    monkeypatch.setattr(transport.settings, "smtp_use_starttls", False)
    monkeypatch.setattr(transport.settings, "smtp_use_ssl", False)

    with (
        patch("app.domains.notifications.transport.smtplib.SMTP") as smtp_ctor,
        pytest.raises(EmailDeliveryError),
    ):
        smtp_instance = MagicMock()
        smtp_instance.send_message.side_effect = smtplib.SMTPException("nope")
        smtp_ctx = MagicMock()
        smtp_ctx.__enter__.return_value = smtp_instance
        smtp_ctx.__exit__.return_value = None
        smtp_ctor.return_value = smtp_ctx
        deliver_plain_email(to_addresses=["t@test"], subject="S", body="B")

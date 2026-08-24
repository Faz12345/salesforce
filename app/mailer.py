"""SMTP email delivery for account recovery messages."""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app


logger = logging.getLogger(__name__)


def is_configured():
    return all(
        current_app.config.get(key)
        for key in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "MAIL_FROM")
    )


def send_password_reset_email(recipient, reset_token):
    """Send a one-hour password reset link over authenticated SMTP."""
    if not is_configured():
        return False

    reset_url = f"{current_app.config['APP_BASE_URL'].rstrip('/')}/reset-password?token={reset_token}"
    message = EmailMessage()
    message["Subject"] = "Reset your Support CRM password"
    message["From"] = current_app.config["MAIL_FROM"]
    message["To"] = recipient
    message.set_content(
        "We received a request to reset your Support CRM password.\n\n"
        f"Reset it here (the link expires in one hour):\n{reset_url}\n\n"
        "If you did not request this, you can safely ignore this email."
    )

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(
            current_app.config["SMTP_HOST"], current_app.config["SMTP_PORT"], timeout=15
        ) as smtp:
            if current_app.config["SMTP_USE_TLS"]:
                smtp.starttls(context=context)
            smtp.login(
                current_app.config["SMTP_USERNAME"], current_app.config["SMTP_PASSWORD"]
            )
            smtp.send_message(message)
        return True
    except (OSError, smtplib.SMTPException):
        logger.exception("Password reset email delivery failed")
        return False

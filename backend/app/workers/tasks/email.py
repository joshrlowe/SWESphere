"""Email-related Celery tasks."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.tasks.email.send_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_email(
    self,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> bool:
    """
    Send an email asynchronously.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML email body
        text_body: Plain text email body (optional)

    Returns:
        True if email was sent successfully
    """
    if not settings.MAIL_SERVER:
        logger.warning("Email not configured, skipping send")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.MAIL_FROM
        msg["To"] = to_email

        # Attach text version if provided
        if text_body:
            msg.attach(MIMEText(text_body, "plain"))

        # Attach HTML version
        msg.attach(MIMEText(html_body, "html"))

        # Connect and send
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            if settings.MAIL_USE_TLS:
                server.starttls()
            if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.sendmail(settings.MAIL_FROM, to_email, msg.as_string())

        logger.info(f"Email sent to {to_email}")
        return True

    except Exception as exc:
        logger.error(f"Failed to send email to {to_email}: {exc}")
        # Retry the task
        raise self.retry(exc=exc)


@celery_app.task(name="app.workers.tasks.email.send_welcome_email")
def send_welcome_email(user_email: str, username: str) -> bool:
    """Send welcome email to new user."""
    subject = f"Welcome to {settings.APP_NAME}!"
    html_body = f"""
    <html>
    <body>
        <h1>Welcome to {settings.APP_NAME}, {username}!</h1>
        <p>We're excited to have you join our community.</p>
        <p>Start exploring and connecting with others today!</p>
        <br>
        <p>Best regards,<br>The {settings.APP_NAME} Team</p>
    </body>
    </html>
    """
    text_body = f"""
    Welcome to {settings.APP_NAME}, {username}!

    We're excited to have you join our community.
    Start exploring and connecting with others today!

    Best regards,
    The {settings.APP_NAME} Team
    """

    return send_email.delay(user_email, subject, html_body, text_body)


@celery_app.task(name="app.workers.tasks.email.send_password_reset_email")
def send_password_reset_email(user_email: str, reset_token: str) -> bool:
    """Send password reset email."""
    reset_url = f"https://swesphere.com/reset-password?token={reset_token}"
    subject = f"{settings.APP_NAME} - Password Reset Request"
    html_body = f"""
    <html>
    <body>
        <h1>Password Reset Request</h1>
        <p>You requested to reset your password.</p>
        <p>Click the link below to reset your password:</p>
        <p><a href="{reset_url}">Reset Password</a></p>
        <p>This link will expire in 1 hour.</p>
        <p>If you didn't request this, please ignore this email.</p>
        <br>
        <p>Best regards,<br>The {settings.APP_NAME} Team</p>
    </body>
    </html>
    """
    text_body = f"""
    Password Reset Request

    You requested to reset your password.
    Click the link below to reset your password:

    {reset_url}

    This link will expire in 1 hour.
    If you didn't request this, please ignore this email.

    Best regards,
    The {settings.APP_NAME} Team
    """

    return send_email.delay(user_email, subject, html_body, text_body)


@celery_app.task(name="app.workers.tasks.email.send_email_verification")
def send_email_verification(user_email: str, verification_token: str) -> bool:
    """Send email verification."""
    verify_url = f"https://swesphere.com/verify-email?token={verification_token}"
    subject = f"{settings.APP_NAME} - Verify Your Email"
    html_body = f"""
    <html>
    <body>
        <h1>Verify Your Email</h1>
        <p>Please verify your email address by clicking the link below:</p>
        <p><a href="{verify_url}">Verify Email</a></p>
        <p>This link will expire in 24 hours.</p>
        <br>
        <p>Best regards,<br>The {settings.APP_NAME} Team</p>
    </body>
    </html>
    """
    text_body = f"""
    Verify Your Email

    Please verify your email address by clicking the link below:

    {verify_url}

    This link will expire in 24 hours.

    Best regards,
    The {settings.APP_NAME} Team
    """

    return send_email.delay(user_email, subject, html_body, text_body)


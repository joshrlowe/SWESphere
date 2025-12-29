"""
Email-related Celery tasks.

Handles all email sending operations including:
- Welcome emails
- Email verification
- Password reset
- Notification digests

All tasks use exponential backoff for retries.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from celery import Task

from app.config import settings
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

MAX_RETRIES = 3
RETRY_BACKOFF = 60  # Base delay in seconds (60, 120, 240 for exponential)

# Email templates base URL
BASE_URL = "https://swesphere.com"  # TODO: Move to settings


# =============================================================================
# Base Email Task
# =============================================================================

class BaseEmailTask(Task):
    """Base class for email tasks with common retry logic."""
    
    autoretry_for = (smtplib.SMTPException, ConnectionError, TimeoutError)
    retry_backoff = True  # Enable exponential backoff
    retry_backoff_max = 600  # Max 10 minutes between retries
    retry_jitter = True  # Add randomness to avoid thundering herd
    max_retries = MAX_RETRIES
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure after all retries exhausted."""
        logger.error(
            f"Email task {self.name} failed permanently after {self.max_retries} retries. "
            f"Args: {args}, Error: {exc}"
        )


# =============================================================================
# Core Email Sending
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.email_tasks.send_email",
    base=BaseEmailTask,
    bind=True,
)
def send_email(
    self,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> dict[str, Any]:
    """
    Send an email asynchronously.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML email body
        text_body: Plain text email body (optional, auto-generated if not provided)

    Returns:
        Dict with status and message ID
        
    Raises:
        SMTPException: On SMTP errors (will retry)
        ConnectionError: On connection failures (will retry)
    """
    # Skip if email is not configured
    if not settings.MAIL_ENABLED or not settings.MAIL_SERVER:
        logger.warning(f"Email not configured, skipping send to {to_email}")
        return {"status": "skipped", "reason": "email_not_configured"}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
        msg["To"] = to_email
        msg["X-Mailer"] = f"{settings.APP_NAME} Mailer"

        # Generate text body from HTML if not provided
        if not text_body:
            # Simple HTML to text conversion (basic)
            import re
            text_body = re.sub(r"<[^>]+>", "", html_body)
            text_body = re.sub(r"\s+", " ", text_body).strip()

        # Attach both versions
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Connect and send
        if settings.MAIL_USE_SSL:
            server = smtplib.SMTP_SSL(settings.MAIL_SERVER, settings.MAIL_PORT)
        else:
            server = smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT)
            if settings.MAIL_USE_TLS:
                server.starttls()

        with server:
            if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
                server.login(
                    settings.MAIL_USERNAME,
                    settings.MAIL_PASSWORD.get_secret_value(),
                )
            server.sendmail(settings.MAIL_FROM, to_email, msg.as_string())

        logger.info(f"Email sent successfully to {to_email}: {subject}")
        return {"status": "sent", "to": to_email, "subject": subject}

    except smtplib.SMTPException as exc:
        logger.warning(
            f"SMTP error sending to {to_email}, attempt {self.request.retries + 1}/{MAX_RETRIES}: {exc}"
        )
        raise  # Will be caught by autoretry_for


# =============================================================================
# Welcome Email
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.email_tasks.send_welcome_email",
    base=BaseEmailTask,
    bind=True,
)
def send_welcome_email(self, user_email: str, username: str) -> dict[str, Any]:
    """
    Send welcome email to newly registered user.
    
    Args:
        user_email: User's email address
        username: User's display name
        
    Returns:
        Result from send_email task
    """
    subject = f"Welcome to {settings.APP_NAME}! 🎉"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; }}
            .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #6b7280; font-size: 12px; padding: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to {settings.APP_NAME}!</h1>
            </div>
            <div class="content">
                <h2>Hey {username}! 👋</h2>
                <p>We're thrilled to have you join our community of developers, creators, and tech enthusiasts.</p>
                <p>Here's what you can do next:</p>
                <ul>
                    <li>🔧 Complete your profile and add an avatar</li>
                    <li>👥 Follow other users to see their posts</li>
                    <li>📝 Share your first post with the community</li>
                    <li>💬 Engage with others through comments and likes</li>
                </ul>
                <a href="{BASE_URL}/explore" class="button">Start Exploring</a>
                <p>If you have any questions, feel free to reach out!</p>
            </div>
            <div class="footer">
                <p>© {settings.APP_NAME} | <a href="{BASE_URL}/unsubscribe">Unsubscribe</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Welcome to {settings.APP_NAME}!

Hey {username}! 👋

We're thrilled to have you join our community of developers, creators, and tech enthusiasts.

Here's what you can do next:
- Complete your profile and add an avatar
- Follow other users to see their posts
- Share your first post with the community
- Engage with others through comments and likes

Start exploring: {BASE_URL}/explore

If you have any questions, feel free to reach out!

© {settings.APP_NAME}
    """

    return send_email.delay(user_email, subject, html_body, text_body)


# =============================================================================
# Email Verification
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.email_tasks.send_verification_email",
    base=BaseEmailTask,
    bind=True,
)
def send_verification_email(self, user_email: str, verification_url: str) -> dict[str, Any]:
    """
    Send email verification link.
    
    Args:
        user_email: User's email address
        verification_url: Complete verification URL with token
        
    Returns:
        Result from send_email task
    """
    subject = f"Verify your email - {settings.APP_NAME}"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 10px; }}
            .button {{ display: inline-block; background: #10b981; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; }}
            .warning {{ background: #fef3c7; border: 1px solid #f59e0b; padding: 15px; border-radius: 6px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #6b7280; font-size: 12px; padding: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="content">
                <h1>Verify Your Email Address</h1>
                <p>Thanks for signing up! Please verify your email address to complete your registration.</p>
                <a href="{verification_url}" class="button">Verify Email Address</a>
                <div class="warning">
                    <strong>⏰ This link expires in 24 hours.</strong>
                    <p style="margin: 5px 0 0 0;">If you didn't create an account, please ignore this email.</p>
                </div>
                <p style="color: #6b7280; font-size: 12px;">
                    If the button doesn't work, copy and paste this URL into your browser:<br>
                    <a href="{verification_url}" style="word-break: break-all;">{verification_url}</a>
                </p>
            </div>
            <div class="footer">
                <p>© {settings.APP_NAME}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Verify Your Email Address

Thanks for signing up! Please verify your email address to complete your registration.

Click the link below to verify:
{verification_url}

⏰ This link expires in 24 hours.

If you didn't create an account, please ignore this email.

© {settings.APP_NAME}
    """

    return send_email.delay(user_email, subject, html_body, text_body)


# =============================================================================
# Password Reset
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.email_tasks.send_password_reset_email",
    base=BaseEmailTask,
    bind=True,
)
def send_password_reset_email(self, user_email: str, reset_url: str) -> dict[str, Any]:
    """
    Send password reset link.
    
    Args:
        user_email: User's email address
        reset_url: Complete password reset URL with token
        
    Returns:
        Result from send_email task
    """
    subject = f"Reset your password - {settings.APP_NAME}"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 10px; }}
            .button {{ display: inline-block; background: #ef4444; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; }}
            .warning {{ background: #fef3c7; border: 1px solid #f59e0b; padding: 15px; border-radius: 6px; margin: 20px 0; }}
            .security {{ background: #fee2e2; border: 1px solid #ef4444; padding: 15px; border-radius: 6px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #6b7280; font-size: 12px; padding: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="content">
                <h1>Reset Your Password</h1>
                <p>We received a request to reset your password. Click the button below to choose a new password.</p>
                <a href="{reset_url}" class="button">Reset Password</a>
                <div class="warning">
                    <strong>⏰ This link expires in 1 hour.</strong>
                </div>
                <div class="security">
                    <strong>🔒 Didn't request this?</strong>
                    <p style="margin: 5px 0 0 0;">If you didn't request a password reset, please ignore this email. Your password will remain unchanged.</p>
                </div>
                <p style="color: #6b7280; font-size: 12px;">
                    If the button doesn't work, copy and paste this URL into your browser:<br>
                    <a href="{reset_url}" style="word-break: break-all;">{reset_url}</a>
                </p>
            </div>
            <div class="footer">
                <p>© {settings.APP_NAME}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Reset Your Password

We received a request to reset your password. Click the link below to choose a new password:

{reset_url}

⏰ This link expires in 1 hour.

🔒 Didn't request this?
If you didn't request a password reset, please ignore this email. Your password will remain unchanged.

© {settings.APP_NAME}
    """

    return send_email.delay(user_email, subject, html_body, text_body)


# =============================================================================
# Notification Digest
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.email_tasks.send_notification_digest",
    base=BaseEmailTask,
    bind=True,
)
def send_notification_digest(
    self,
    user_email: str,
    username: str,
    notifications: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Send daily/weekly notification digest.
    
    Args:
        user_email: User's email address
        username: User's display name
        notifications: List of notification summaries
        
    Returns:
        Result from send_email task
    """
    count = len(notifications)
    subject = f"You have {count} new notification{'s' if count != 1 else ''} - {settings.APP_NAME}"
    
    # Build notification list HTML
    notification_items = ""
    for notif in notifications[:10]:  # Limit to 10 in email
        notification_items += f"""
        <li style="padding: 10px 0; border-bottom: 1px solid #e5e7eb;">
            <strong>{notif.get('type', 'Notification')}</strong>
            <p style="margin: 5px 0; color: #6b7280;">{notif.get('message', '')}</p>
        </li>
        """
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #4f46e5; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; }}
            .button {{ display: inline-block; background: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #6b7280; font-size: 12px; padding: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📬 Your Daily Digest</h1>
            </div>
            <div class="content">
                <h2>Hey {username}!</h2>
                <p>You have <strong>{count} new notification{'s' if count != 1 else ''}</strong> waiting for you.</p>
                <ul style="list-style: none; padding: 0;">
                    {notification_items}
                </ul>
                {"<p><em>...and more</em></p>" if count > 10 else ""}
                <a href="{BASE_URL}/notifications" class="button">View All Notifications</a>
            </div>
            <div class="footer">
                <p>© {settings.APP_NAME} | <a href="{BASE_URL}/settings/notifications">Manage email preferences</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Your Daily Digest - {settings.APP_NAME}

Hey {username}!

You have {count} new notification{'s' if count != 1 else ''} waiting for you.

View all: {BASE_URL}/notifications

© {settings.APP_NAME}
    """

    return send_email.delay(user_email, subject, html_body, text_body)


"""
Email service using SMTP

Sends transactional emails for:
- User verification
- Password reset
- Trial expiring warnings
- Quota exceeded notifications
- Job completion alerts

Simple, reliable SMTP-based email delivery.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from dataclasses import dataclass

from apps.shared.utils.logger import get_logger
from config import settings

logger = get_logger(__name__)


@dataclass
class EmailMessage:
    """Email message structure."""
    to: List[str]
    subject: str
    html_body: str
    text_body: Optional[str] = None
    from_email: Optional[str] = None
    reply_to: Optional[str] = None


class EmailService:
    """
    SMTP email service.

    Sends HTML and plain text emails via SMTP.

    Configuration (from settings):
        - SMTP_HOST: SMTP server hostname
        - SMTP_PORT: SMTP server port
        - SMTP_USERNAME: SMTP username
        - SMTP_PASSWORD: SMTP password
        - SMTP_FROM_EMAIL: Default from address
        - SMTP_USE_TLS: Use TLS encryption

    Usage:
        email_service = EmailService()

        await email_service.send_email(
            to=["user@example.com"],
            subject="Welcome!",
            html_body="<h1>Welcome to Creator</h1>",
        )
    """

    def __init__(self):
        """Initialize email service."""
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.use_tls = settings.SMTP_USE_TLS

        logger.info(
            "email_service_initialized",
            smtp_host=self.smtp_host,
            smtp_port=self.smtp_port,
        )

    async def send_email(
        self,
        to: List[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> bool:
        """
        Send an email.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional, auto-generated if not provided)
            from_email: From address (defaults to SMTP_FROM_EMAIL)
            reply_to: Reply-to address (optional)

        Returns:
            True if sent successfully

        Example:
            >>> success = await email_service.send_email(
            ...     to=["user@example.com"],
            ...     subject="Your job is complete!",
            ...     html_body="<h1>Job Complete</h1><p>Your image is ready.</p>",
            ... )
        """
        # Use default from email if not provided
        from_email = from_email or self.from_email

        # Create message
        message = MIMEMultipart("alternative")
        message["From"] = from_email
        message["To"] = ", ".join(to)
        message["Subject"] = subject

        if reply_to:
            message["Reply-To"] = reply_to

        # Attach text part (plain text fallback)
        if text_body:
            text_part = MIMEText(text_body, "plain")
            message.attach(text_part)

        # Attach HTML part
        html_part = MIMEText(html_body, "html")
        message.attach(html_part)

        try:
            # Connect to SMTP server
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)

            # Login if credentials provided
            if self.username and self.password:
                server.login(self.username, self.password)

            # Send email
            server.sendmail(from_email, to, message.as_string())
            server.quit()

            logger.info(
                "email_sent",
                to=to,
                subject=subject,
            )

            return True

        except Exception as e:
            logger.error(
                "email_send_failed",
                to=to,
                subject=subject,
                error=str(e),
                exc_info=True,
            )
            return False

    async def send_verification_email(self, to: str, verification_link: str) -> bool:
        """
        Send email verification email.

        Args:
            to: User email address
            verification_link: Verification URL

        Returns:
            True if sent successfully
        """
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background: #3b82f6;
                    color: white;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 600;
                }}
                .footer {{ margin-top: 40px; color: #6b7280; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Verify your email</h1>
                <p>Thanks for signing up! Please verify your email address to get started.</p>
                <p style="margin: 30px 0;">
                    <a href="{verification_link}" class="button">Verify Email</a>
                </p>
                <p class="footer">
                    If you didn't create an account, you can safely ignore this email.
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to=[to],
            subject="Verify your email address",
            html_body=html_body,
        )

    async def send_job_completed_email(
        self,
        to: str,
        job_id: str,
        result_url: str,
    ) -> bool:
        """
        Send job completion notification.

        Args:
            to: User email address
            job_id: Job ID
            result_url: URL to view/download result

        Returns:
            True if sent successfully
        """
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background: #10b981;
                    color: white;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 600;
                }}
                .success {{ color: #10b981; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="success">✓ Job Complete!</h1>
                <p>Your image processing job is ready.</p>
                <p><strong>Job ID:</strong> {job_id}</p>
                <p style="margin: 30px 0;">
                    <a href="{result_url}" class="button">View Result</a>
                </p>
                <p style="color: #6b7280; font-size: 14px;">
                    The result has been saved to your Google Drive.
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to=[to],
            subject=f"Job {job_id[:8]} is complete!",
            html_body=html_body,
        )

    async def send_quota_warning_email(
        self,
        to: str,
        remaining_jobs: int,
        reset_date: str,
    ) -> bool:
        """
        Send quota warning email.

        Args:
            to: User email address
            remaining_jobs: Number of jobs remaining
            reset_date: Date when quota resets

        Returns:
            True if sent successfully
        """
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .warning {{ color: #f59e0b; }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background: #3b82f6;
                    color: white;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 600;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="warning">⚠️ Quota Warning</h1>
                <p>You have <strong>{remaining_jobs}</strong> jobs remaining in your monthly quota.</p>
                <p>Your quota will reset on <strong>{reset_date}</strong>.</p>
                <p style="margin: 30px 0;">
                    <a href="#" class="button">Upgrade Plan</a>
                </p>
                <p style="color: #6b7280; font-size: 14px;">
                    Upgrade to Creator or Studio tier for unlimited jobs.
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to=[to],
            subject="Monthly quota running low",
            html_body=html_body,
        )


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """
    Get singleton EmailService instance.

    Returns:
        EmailService instance

    Usage:
        from apps.shared.services.email import get_email_service

        email = get_email_service()
        await email.send_verification_email(user.email, verification_link)
    """
    global _email_service

    if _email_service is None:
        _email_service = EmailService()

    return _email_service

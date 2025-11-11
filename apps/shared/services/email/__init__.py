"""
Email services for notifications
"""

from .smtp_provider import EmailService, EmailMessage, get_email_service

__all__ = ["EmailService", "EmailMessage", "get_email_service"]

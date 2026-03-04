"""
Email sender module using Resend.

This module provides functionality to send emails using the Resend API.
The module supports HTML email content and is designed to be extensible
for other email providers in the future.

Prerequisites:
    - Resend API key (set via RESEND_API_KEY environment variable)
    - Verified sender domain (or use Resend's test domain)

Example:
    >>> sender = EmailSender()
    >>> result = sender.send(
    ...     to=["user@example.com"],
    ...     subject="Hello",
    ...     html="<p>This is a test email</p>"
    ... )
    >>> print(result)
"""

import logging
from typing import Dict, Any, List, Optional

import resend

from src.config import get_config

logger = logging.getLogger(__name__)


class EmailSenderError(Exception):
    """Custom exception for email sender errors."""

    def __init__(self, message: str, error_code: Optional[str] = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            error_code: Optional error code from Resend API
        """
        super().__init__(message)
        self.error_code = error_code


class EmailSender:
    """Email sender using Resend API.

    This class provides a unified interface for sending emails through Resend,
    with support for HTML content and extensible design for other providers.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the email sender.

        Args:
            api_key: Resend API key. Uses config if not provided.
        """
        self.config = get_config()
        self.api_key = api_key or self.config.resend_api_key

        # Configure Resend with API key
        resend.api_key = self.api_key

        logger.info("Email sender initialized")

    def send(
        self,
        to: List[str],
        subject: str,
        html: str,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an HTML email.

        Args:
            to: List of recipient email addresses
            subject: Email subject line
            html: HTML content of the email
            from_email: Sender email address. Uses config if not provided.
            reply_to: Reply-to email address

        Returns:
            Dictionary containing the response from Resend API

        Raises:
            EmailSenderError: If sending fails
        """
        from_email = from_email or self.config.email_from

        params: resend.Emails.SendParams = {
            "from": from_email,
            "to": to,
            "subject": subject,
            "html": html,
        }

        if reply_to:
            params["reply_to"] = reply_to

        try:
            logger.info(f"Sending email to {to}, subject: {subject}")

            result = resend.Emails.send(params)

            logger.info(f"Email sent successfully: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise EmailSenderError(f"Failed to send email: {e}") from e

    def send_campaign(
        self,
        subject: str,
        html: str,
        from_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a campaign email to all configured recipients.

        Args:
            subject: Email subject line
            html: HTML content of the email
            from_email: Sender email address. Uses config if not provided.

        Returns:
            Dictionary containing the response from Resend API

        Raises:
            EmailSenderError: If sending fails
        """
        recipients = self.config.email_to

        if not recipients:
            raise EmailSenderError("No recipients configured")

        logger.info(f"Sending campaign to {len(recipients)} recipients")

        return self.send(
            to=recipients,
            subject=subject,
            html=html,
            from_email=from_email,
        )


class EmailProvider:
    """Base class for email providers.

    This class provides a provider-agnostic interface,
    allowing easy switching between different email backends.

    To add a new provider:
        1. Create a new class that extends EmailProvider
        2. Implement the send() method
        3. Update the factory in get_email_provider()
    """

    def send(
        self,
        to: List[str],
        subject: str,
        html: str,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an HTML email (to be implemented by subclasses)."""
        raise NotImplementedError("Subclasses must implement send()")


class ResendEmailSender(EmailSender, EmailProvider):
    """Email sender using Resend API.

    This class provides a unified interface for sending emails through Resend,
    with support for HTML content and extensible design for other providers.
    """

    pass


def get_email_provider(provider_type: str = "resend") -> EmailProvider:
    """Factory function to get an email provider.

    Args:
        provider_type: Type of email provider ("resend" for now)

    Returns:
        EmailProvider instance

    Raises:
        ValueError: If provider_type is not supported
    """
    if provider_type.lower() == "resend":
        return ResendEmailSender()
    else:
        raise ValueError(f"Unsupported email provider: {provider_type}")

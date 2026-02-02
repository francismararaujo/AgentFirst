
"""Email Service for AgentFirst2 MVP

This module provides email sending capabilities using AWS SES.
"""

import boto3
import logging
from typing import Optional, List, Dict, Any
from botocore.exceptions import ClientError
from app.config.settings import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via AWS SES"""

    def __init__(self, region_name: Optional[str] = None):
        """Initialize SES client"""
        self.region_name = region_name or settings.AWS_REGION
        self.client = boto3.client("ses", region_name=self.region_name)
        self.sender = settings.SENDER_EMAIL

    def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        source: Optional[str] = None,
    ) -> bool:
        """
        Send an email

        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            source: Sender email address (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            destination = {"ToAddresses": to_addresses}
            message = {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body_text, "Charset": "UTF-8"}},
            }

            if body_html:
                message["Body"]["Html"] = {"Data": body_html, "Charset": "UTF-8"}

            response = self.client.send_email(
                Source=source or self.sender,
                Destination=destination,
                Message=message,
            )

            logger.info(f"Email sent successfully. MessageId: {response['MessageId']}")
            return True

        except ClientError as e:
            logger.error(f"Failed to send email: {e.response['Error']['Message']}")
            return False

    def send_otp_email(self, to_email: str, otp_code: str) -> bool:
        """
        Send OTP verification email

        Args:
            to_email: Recipient email
            otp_code: 6-digit OTP code

        Returns:
            True if sent successfully, False otherwise
        """
        subject = f"Seu código de verificação AgentFirst: {otp_code}"
        
        body_text = (
            f"Olá,\n\n"
            f"Seu código de verificação para o AgentFirst é: {otp_code}\n\n"
            f"Este código expira em 5 minutos.\n\n"
            f"Se você não solicitou este código, ignore este e-mail."
        )

        body_html = f"""
        <html>
        <head></head>
        <body>
            <h1>Código de Verificação</h1>
            <p>Olá,</p>
            <p>Seu código de verificação para o <strong>AgentFirst</strong> é:</p>
            <h2 style="color: #2E86C1; letter-spacing: 5px;">{otp_code}</h2>
            <p>Este código expira em 5 minutos.</p>
            <p style="font-size: 12px; color: #666;">Se você não solicitou este código, ignore este e-mail.</p>
        </body>
        </html>
        """

        # Ensure we are not sending from a non-verified email in sandbox if not configured
        # Ideally, settings.SENDER_EMAIL should be verified in SES
        return self.send_email(
            to_addresses=[to_email],
            subject=subject,
            body_text=body_text,
            body_html=body_html
        )

"""
SMTP Email Client

Sends outreach email via any SMTP provider (Gmail app passwords, Outlook,
transactional relays...). This is the Phase 3 sending provider; SES / Gmail
API / Graph integrations can be added later behind the same interface.
"""

import logging
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class SMTPSendError(Exception):
    """Raised when an SMTP send fails."""


@dataclass
class SentMessage:
    """Result of a successful SMTP send."""

    message_id: str
    provider: str = "smtp"


class SMTPClient:
    """Sends plain-text email via SMTP with STARTTLS."""

    def __init__(
        self,
        host: str = "",
        port: int = 587,
        username: str = "",
        password: str = "",
        use_tls: bool = True,
    ) -> None:
        self.host = host or settings.smtp_host
        self.port = port or settings.smtp_port
        self.username = username or settings.smtp_user
        self.password = password or settings.smtp_password
        self.use_tls = use_tls

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.username and self.password)

    async def send(
        self,
        *,
        from_addr: str,
        from_name: str,
        to_addr: str,
        subject: str,
        body: str,
        reply_to: str = "",
    ) -> SentMessage:
        """
        Send one plain-text email.

        Raises:
            SMTPSendError: On any SMTP failure (connection, auth, rejection).
        """
        if not self.is_configured:
            raise SMTPSendError(
                "SMTP is not configured - set SMTP_HOST, SMTP_USER and SMTP_PASSWORD"
            )

        message = MIMEMultipart()
        message["From"] = formataddr((from_name, from_addr))
        message["To"] = to_addr
        message["Subject"] = subject
        if reply_to:
            message["Reply-To"] = reply_to
        message["Message-ID"] = make_msgid(domain=from_addr.split("@")[-1])
        message.attach(MIMEText(body, "plain", "utf-8"))

        try:
            await aiosmtplib.send(
                message,
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                start_tls=self.use_tls,
            )
        except (aiosmtplib.SMTPException, ConnectionError, OSError) as exc:
            logger.error("SMTP send to %s failed: %s", to_addr, exc)
            raise SMTPSendError(f"SMTP send failed: {exc}") from exc

        message_id = message["Message-ID"] or ""
        logger.info("Email sent to %s (message-id=%s)", to_addr, message_id)
        return SentMessage(message_id=message_id)


smtp_client = SMTPClient()

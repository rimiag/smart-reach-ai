"""
IMAP Client

Fetches recent inbound emails from a mailbox via IMAP (stdlib imaplib - no
extra dependency). Returns raw replies for the reply monitor to match against
sent outreach emails.

Only messages received since the last check are returned; the caller tracks
the high-water mark (latest received date seen).
"""

import email
import imaplib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


class ImapError(Exception):
    """Raised when the mailbox cannot be reached or read."""


@dataclass
class RawReply:
    """One raw inbound email, pre-matching."""

    from_email: str
    from_name: str
    subject: str
    body: str
    in_reply_to: str
    received_at: Optional[datetime]


def _decode(value) -> str:
    """Decode a MIME-encoded header value into a plain string."""
    if value is None:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return str(value)


def _extract_body(message) -> str:
    """Extract the plain-text body of an email.message.Message."""
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        return payload.decode(charset, errors="replace")
                    except LookupError:
                        return payload.decode("utf-8", errors="replace")
        return ""
    payload = message.get_payload(decode=True)
    if payload is None:
        return str(message.get_payload())
    charset = message.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


class ImapClient:
    """Reads unread inbound emails from an IMAP mailbox."""

    def __init__(
        self,
        host: str = "",
        port: int = 993,
        username: str = "",
        password: str = "",
        folder: str = "INBOX",
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.folder = folder

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.username and self.password)

    def fetch_since(self, since: datetime, limit: int = 100) -> list:
        """
        Fetch unread messages received since ``since`` (UTC), oldest first.

        Args:
            since: Only messages with an internal date after this are returned.
            limit: Safety cap on the number of messages per check.

        Raises:
            ImapError: On connection or fetch failure.
        """
        if not self.is_configured:
            raise ImapError("IMAP is not configured - set IMAP_HOST, IMAP_USER and IMAP_PASSWORD")

        since_date = (since - timedelta(hours=1)).strftime("%d-%b-%Y")
        replies: list = []

        try:
            mail = imaplib.IMAP4_SSL(self.host, self.port)
            mail.login(self.username, self.password)
            try:
                mail.select(self.folder, readonly=True)
                # No UNSEEN filter: replies you've already read in your mail
                # client must still be found. Dedup happens at ingest.
                status, data = mail.search(None, f'SINCE "{since_date}"')
                if status != "OK":
                    raise ImapError(f"IMAP search failed: {status}")

                ids = data[0].split()[:limit]
                for mail_id in ids:
                    status, msg_data = mail.fetch(mail_id, "(RFC822)")
                    if status != "OK" or not msg_data or msg_data[0] is None:
                        continue
                    raw_bytes = msg_data[0][1]
                    try:
                        message = email.message_from_bytes(raw_bytes)
                    except Exception as exc:
                        logger.warning("Skipping unparseable message %s: %s", mail_id, exc)
                        continue

                    from_name, from_email = parseaddr(_decode(message.get("From", "")))
                    received_at = None
                    try:
                        received_at = parsedate_to_datetime(message.get("Date"))
                    except Exception:
                        received_at = None

                    # Prefer In-Reply-To; fall back to the last References entry
                    # (the closest ancestor in the thread).
                    in_reply_to = _decode(message.get("In-Reply-To", ""))
                    if not in_reply_to:
                        references = _decode(message.get("References", "")).split()
                        in_reply_to = references[-1] if references else ""

                    replies.append(
                        RawReply(
                            from_email=from_email.lower(),
                            from_name=from_name,
                            subject=_decode(message.get("Subject", "")),
                            body=_extract_body(message),
                            in_reply_to=in_reply_to,
                            received_at=(
                                received_at.replace(tzinfo=None)
                                if received_at and received_at.tzinfo
                                else received_at
                            ),
                        )
                    )
            finally:
                try:
                    mail.logout()
                except Exception:
                    pass
        except imaplib.IMAP4.error as exc:
            raise ImapError(f"IMAP error: {exc}") from exc
        except (ConnectionError, OSError) as exc:
            raise ImapError(f"IMAP connection failed: {exc}") from exc

        logger.info("IMAP fetch: %d unread message(s) since %s", len(replies), since_date)
        return replies

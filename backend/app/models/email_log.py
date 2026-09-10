"""
Email Log Model

Audit trail for every outreach email the system attempts to send (Phase 3).
One row per send attempt, linked to its lead and campaign.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.mysql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

EMAIL_STATUS = ENUM(
    "sent",
    "failed",
    "bounced",
    name="email_log_status",
)


class EmailLog(Base):
    """One outbound outreach email (attempt) with its outcome."""

    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(EMAIL_STATUS, default="sent", nullable=False, index=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    unsubscribe_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<EmailLog(id={self.id}, lead_id={self.lead_id}, "
            f"to={self.to_email}, status={self.status})>"
        )

"""
Reply Model

An inbound email reply to one of our outreach emails (Phase 4). Replies are
matched to sent emails via Message-ID headers or sender address, classified
by AI into a category, and drive lead status updates.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.mysql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

REPLY_CATEGORY = ENUM(
    "interested",
    "not_interested",
    "need_more_info",
    "request_meeting",
    "pricing_request",
    "out_of_office",
    "unsubscribe",
    "wrong_contact",
    "other",
    name="reply_category",
)

REPLY_STATUS = ENUM("unread", "read", name="reply_status")


class Reply(Base):
    """An inbound reply from a lead."""

    __tablename__ = "replies"

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

    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    category: Mapped[str] = mapped_column(
        REPLY_CATEGORY, default="other", nullable=False, index=True
    )
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    classification_error: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(REPLY_STATUS, default="unread", nullable=False)

    # The Message-ID of the outreach email this reply references (dedup key).
    # 191 chars: unique index stays under MariaDB's 767-byte key limit (utf8mb4).
    in_reply_to: Mapped[Optional[str]] = mapped_column(String(191), nullable=True, unique=True)

    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Reply(id={self.id}, lead_id={self.lead_id}, category={self.category})>"

"""
Suppression Model

Emails that must never be contacted: unsubscribes, bounces, and manual
entries. Checked before every send (Phase 3 compliance requirement).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.mysql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

SUPPRESSION_REASON = ENUM(
    "unsubscribed",
    "bounced",
    "manual",
    name="suppression_reason",
)


class Suppression(Base):
    """A contact that must never receive outreach email."""

    __tablename__ = "suppressions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 190 chars: keeps the utf8mb4 composite unique index under MariaDB's
    # 767-byte key limit (190*4 + 4 = 764 bytes).
    email: Mapped[str] = mapped_column(String(190), nullable=False, index=True)

    reason: Mapped[str] = mapped_column(SUPPRESSION_REASON, default="manual", nullable=False)
    lead_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("leads.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "email", name="uq_suppression_user_email"),)

    def __repr__(self) -> str:
        return f"<Suppression(id={self.id}, email={self.email}, reason={self.reason})>"

"""
Lead Model

Database model for discovered business contacts and leads.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.mysql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# Lead status enum
LEAD_STATUS = ENUM(
    "new",            # Just discovered
    "researching",    # Being processed
    "qualified",      # AI qualified
    "review",         # Ready for human review
    "approved",       # Approved for outreach
    "rejected",       # Rejected by user
    "scheduled",      # Email scheduled
    "sent",            # Email sent
    "replied",        # Got a reply
    "interested",     # Expressed interest
    "not_interested", # Not interested
    "unsubscribed",   # Unsubscribed
    "bounced",        # Email bounced
    "do_not_contact", # Blocked
    name="lead_status",
)


class Lead(Base):
    """
    Lead model for storing discovered business contacts and leads.

    A lead represents a potential customer discovered through web search
    and crawling, qualified by AI, and managed through the outreach workflow.
    """

    __tablename__ = "leads"

    # ------------------------------------------------------------------
    # Primary Key
    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # ------------------------------------------------------------------
    # Foreign Keys
    # ------------------------------------------------------------------
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Source Information
    # ------------------------------------------------------------------
    keyword: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    source_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    contact_page_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Organization Details
    # ------------------------------------------------------------------
    organization_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    website: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Contact Information
    # ------------------------------------------------------------------
    contact_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    job_title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    department: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------
    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # AI Qualification
    # ------------------------------------------------------------------
    lead_score: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    ai_reasoning: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Status & Email Campaign
    # ------------------------------------------------------------------
    status: Mapped[str] = mapped_column(
        LEAD_STATUS,
        default="new",
        nullable=False,
    )

    generated_email: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    email_template_id: Mapped[Optional[int]] = mapped_column(
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Tracking
    # ------------------------------------------------------------------
    emails_sent: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    last_emailed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Opt-out
    # ------------------------------------------------------------------
    do_not_contact: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    unsubscribed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Timestamps (MariaDB 10.1 doesn't support timezone in DateTime)
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    qualified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    campaign: Mapped["Campaign"] = relationship(
        back_populates="leads",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<Lead(id={self.id}, "
            f"organization={self.organization_name}, "
            f"status={self.status})>"
        )
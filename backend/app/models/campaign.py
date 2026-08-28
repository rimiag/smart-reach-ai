"""
Campaign Model

Database model for lead generation campaigns.
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.mysql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db.base import Base


class JSONText(TypeDecorator):
    """
    Store Python dictionaries/lists as JSON text in MariaDB.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)


# Campaign status enum
CAMPAIGN_STATUS = ENUM(
    "draft",
    "researching",
    "ready",
    "active",
    "paused",
    "completed",
    name="campaign_status",
)


class Campaign(Base):
    """
    Campaign model for organizing lead generation activities.

    A campaign contains keywords for searching and tracks the progress
    of lead discovery and outreach.
    """

    __tablename__ = "campaigns"

    # Primary Key
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # Foreign Key
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Campaign Details
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Status
    status: Mapped[str] = mapped_column(
        CAMPAIGN_STATUS,
        default="draft",
        nullable=False,
    )

    # Keywords
    # Example:
    # ["software", "healthcare", "AI"]
    keywords: Mapped[list] = mapped_column(
        JSONText,
        nullable=False,
    )

    # Settings
    # Example:
    # {
    #     "max_leads": 100,
    #     "email_enabled": True
    # }
    settings: Mapped[Optional[dict]] = mapped_column(
        JSONText,
        nullable=True,
    )

    # Timestamps (MariaDB 10.1 doesn't support timezone in DateTime)
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

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Relationships
    leads: Mapped[list["Lead"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, " f"name={self.name}, " f"status={self.status})>"

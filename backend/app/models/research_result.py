"""
Research Result Model

Database model for websites discovered during the search phase of a campaign.

Each row represents one discovered website (deduplicated by domain within a
campaign). The crawler phase (Iteration 1.5) picks these up and turns the
promising ones into leads.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.mysql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.campaign import JSONText

# Research result status enum
RESEARCH_RESULT_STATUS = ENUM(
    "discovered",  # Found by the search agent, awaiting processing
    "queued",  # Queued for crawling
    "crawling",  # Currently being crawled
    "crawled",  # Crawled successfully, contact extraction done
    "skipped",  # Filtered out (duplicate domain, low quality, robots.txt, ...)
    "failed",  # Crawling failed
    name="research_result_status",
)


class ResearchResult(Base):
    """
    A website discovered by the search agent for a campaign keyword.

    Domains are unique per campaign: if several keywords surface the same
    domain, the first keyword wins and later ones are recorded only in
    ``extra_data.matched_keywords`` (kept simple: skipped on insert).
    """

    __tablename__ = "research_results"

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
    # Search Source Information
    # ------------------------------------------------------------------
    keyword: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    domain: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    title: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )

    snippet: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Processing Status
    # ------------------------------------------------------------------
    status: Mapped[str] = mapped_column(
        RESEARCH_RESULT_STATUS,
        default="discovered",
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Search Metadata
    # ------------------------------------------------------------------
    provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    result_position: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # Extra provider/search payload (JSON stored as TEXT for MariaDB 10.1)
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSONText,
        nullable=True,
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
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

    crawled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<ResearchResult(id={self.id}, "
            f"campaign_id={self.campaign_id}, "
            f"domain={self.domain}, "
            f"status={self.status})>"
        )

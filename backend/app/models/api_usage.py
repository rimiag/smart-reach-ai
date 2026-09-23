"""
API Usage Counter Model

Monthly request counters per external provider (serpapi, gemini, ...),
rendered in the admin API-usage dashboard. The SerpAPI card prefers the live
SerpApi account endpoint and falls back to these counters.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ApiUsageCounter(Base):
    """One row per (provider, month) with a running request count."""

    __tablename__ = "api_usage_counters"
    __table_args__ = (
        UniqueConstraint("provider", "period", name="uq_api_usage_provider_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Both indexed columns are short strings - safe for MariaDB 10.1's
    # 767-byte utf8mb4 index limit (see users.email note).
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # "YYYY-MM"
    count: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<ApiUsageCounter(provider={self.provider}, period={self.period}, "
            f"count={self.count})>"
        )

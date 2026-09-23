"""
User Model

Database model for user accounts and authentication.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """
    User account model.

    Represents users who can create campaigns and manage leads.
    """

    __tablename__ = "users"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Authentication
    # 191 chars: keeps the utf8mb4 unique index under MariaDB 10.1's
    # 767-byte key limit (191*4 = 764 bytes).
    email: Mapped[str] = mapped_column(String(191), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        Enum("admin", "user", name="user_role"), default="user", nullable=False
    )

    # Timestamps (MariaDB 10.1 doesn't support timezone in DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Email verification. server_default TRUE is what makes ensure_schema's
    # ALTER backfill every EXISTING user as verified when this column is added
    # (they signed up before verification existed). Only the register endpoint
    # creates rows with is_verified=False explicitly.
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("1"), nullable=False
    )
    verification_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    verification_token_expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Billing (admin-managed, informational - no payment gateway)
    # Plain String, not Enum: changing plans must not require an enum ALTER.
    # server_default (not just python default) so ensure_schema's ALTER can
    # backfill existing rows when adding the column to a populated table.
    plan: Mapped[str] = mapped_column(
        String(50), default="free", server_default="free", nullable=False
    )
    billing_status: Mapped[str] = mapped_column(
        String(50), default="active", server_default="active", nullable=False
    )
    billing_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Account access: "hold" = can browse but no consuming actions (campaigns,
    # research, AI, sending) until an admin releases them. server_default keeps
    # EXISTING users active when ensure_schema adds the column; only the
    # register endpoint creates rows with account_status="hold" explicitly.
    account_status: Mapped[str] = mapped_column(
        String(50), default="active", server_default="active", nullable=False
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

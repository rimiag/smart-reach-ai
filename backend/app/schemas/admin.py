"""
Admin Schemas

Request/response models for the admin panel (user management, billing,
overview stats, system health). Every admin endpoint requires the admin role;
see app/api/v1/admin.py.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

Role = Literal["admin", "user"]


# -----------------------------------------------------------------------------
# Users
# -----------------------------------------------------------------------------
class AdminListItem(BaseModel):
    """One row in the admin users/billing tables."""

    id: int
    email: EmailStr
    name: Optional[str] = None
    role: Role
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    # Billing (admin-managed)
    plan: str = "free"
    billing_status: str = "active"
    billing_notes: Optional[str] = None

    # Usage (computed from owned records)
    campaigns_count: int = 0
    leads_count: int = 0
    emails_count: int = 0

    model_config = {"from_attributes": True}


class AdminUsersResponse(BaseModel):
    """Paginated users listing."""

    items: List[AdminListItem]
    total: int
    page: int
    per_page: int


class AdminUserCreate(BaseModel):
    """Admin-created account (no self-registration semantics)."""

    email: EmailStr
    name: Optional[str] = None
    password: str = Field(..., min_length=8, max_length=72, description="Max 72 for bcrypt")
    role: Role = "user"


class AdminUserUpdate(BaseModel):
    """Partial update. Only provided fields are applied."""

    name: Optional[str] = None
    role: Optional[Role] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(
        None, min_length=8, max_length=100, description="Set a new password"
    )
    plan: Optional[str] = Field(None, max_length=50)
    billing_status: Optional[str] = Field(None, max_length=50)
    billing_notes: Optional[str] = None


# -----------------------------------------------------------------------------
# Overview
# -----------------------------------------------------------------------------
class DayCount(BaseModel):
    date: str  # YYYY-MM-DD
    count: int


class RecentSignup(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None
    role: Role
    created_at: datetime

    model_config = {"from_attributes": True}


class OverviewStats(BaseModel):
    users_total: int
    users_active: int
    users_admins: int
    campaigns_total: int
    leads_total: int
    emails_total: int
    replies_total: int
    suppressions_total: int
    emails_last_7_days: List[DayCount]
    recent_signups: List[RecentSignup]


# -----------------------------------------------------------------------------
# System health
# -----------------------------------------------------------------------------
class SystemStatus(BaseModel):
    database: bool
    redis: bool
    celery_online: bool
    celery_workers: List[str]
    # Key/config presence flags only - never values.
    integrations: dict[str, bool]


# -----------------------------------------------------------------------------
# API usage (admin dashboard)
# -----------------------------------------------------------------------------
class ApiUsageInfo(BaseModel):
    """Usage snapshot for one external API provider."""

    configured: bool
    used: Optional[int] = None
    limit: Optional[int] = None
    remaining: Optional[int] = None
    # "live" = provider's own account endpoint, "counter" = our tracking table
    source: str = "counter"
    error: Optional[str] = None


class EmailUsageInfo(BaseModel):
    """Outreach email volume for the current month."""

    configured: bool
    sent_this_month: int
    failed_this_month: int


class ApiUsageResponse(BaseModel):
    """Admin API-usage dashboard payload."""

    serpapi: ApiUsageInfo
    gemini: ApiUsageInfo
    email: EmailUsageInfo

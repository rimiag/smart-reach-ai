"""
Admin API Endpoints

User management, billing status, overview stats and system health.
Every route requires the admin role via the router-level dependency;
mutating routes additionally receive the admin for guard checks.
"""

import logging
from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import get_db
from app.dependencies import get_current_admin
from app.models.campaign import Campaign
from app.models.email_log import EmailLog
from app.models.lead import Lead
from app.models.reply import Reply
from app.models.suppression import Suppression
from app.models.user import User
from app.schemas.admin import (
    AdminListItem,
    AdminUserCreate,
    AdminUsersResponse,
    AdminUserUpdate,
    DayCount,
    OverviewStats,
    RecentSignup,
    SystemStatus,
)
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_admin)])

DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentAdmin = Annotated[UserResponse, Depends(get_current_admin)]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
async def _count(db: AsyncSession, model, *filters) -> int:
    stmt = select(func.count()).select_from(model)
    if filters:
        stmt = stmt.where(*filters)
    return int(await db.scalar(stmt) or 0)


async def _usage_counts(db: AsyncSession, user_id: int) -> tuple:
    """(campaigns, leads, emails) owned by one user - for single-user responses."""
    campaigns = await _count(db, Campaign, Campaign.user_id == user_id)
    leads = await _count(db, Lead, Lead.user_id == user_id)
    emails = await _count(db, EmailLog, EmailLog.user_id == user_id)
    return campaigns, leads, emails


async def _get_user_or_404(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def _guard_not_self(current_admin: UserResponse, target: User, action: str) -> None:
    if target.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You cannot {action} your own account",
        )


async def _guard_last_admin(db: AsyncSession, target: User, action: str) -> None:
    """Refuse to remove the power of the last active admin (demote/deactivate/delete)."""
    if target.role != "admin":
        return
    remaining = await _count(
        db,
        User,
        User.role == "admin",
        User.is_active.is_(True),
        User.id != target.id,
    )
    if remaining == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot {action} the last active admin",
        )


def _to_item(user: User, campaigns: int = 0, leads: int = 0, emails: int = 0) -> AdminListItem:
    item = AdminListItem.model_validate(user)
    item.campaigns_count = campaigns
    item.leads_count = leads
    item.emails_count = emails
    return item


# -----------------------------------------------------------------------------
# Overview
# -----------------------------------------------------------------------------
@router.get("/overview", response_model=OverviewStats)
async def get_overview(db: DBSession):
    """Totals across the platform plus recent signups and 7-day email volume."""
    users_total = await _count(db, User)
    users_active = await _count(db, User, User.is_active.is_(True))
    users_admins = await _count(db, User, User.role == "admin")
    campaigns_total = await _count(db, Campaign)
    leads_total = await _count(db, Lead)
    emails_total = await _count(db, EmailLog)
    replies_total = await _count(db, Reply)
    suppressions_total = await _count(db, Suppression)

    # Emails per day for the last 7 days (missing days filled with 0)
    since = datetime.utcnow() - timedelta(days=6)
    rows = await db.execute(
        select(func.date(EmailLog.created_at).label("day"), func.count())
        .where(EmailLog.created_at >= since)
        .group_by(func.date(EmailLog.created_at))
    )
    per_day = {str(day): int(n) for day, n in rows.all()}
    emails_last_7_days = []
    for i in range(6, -1, -1):
        day = (datetime.utcnow() - timedelta(days=i)).date()
        emails_last_7_days.append(
            DayCount(date=day.isoformat(), count=per_day.get(day.isoformat(), 0))
        )

    recent = (
        (await db.execute(select(User).order_by(User.created_at.desc()).limit(10))).scalars().all()
    )

    return OverviewStats(
        users_total=users_total,
        users_active=users_active,
        users_admins=users_admins,
        campaigns_total=campaigns_total,
        leads_total=leads_total,
        emails_total=emails_total,
        replies_total=replies_total,
        suppressions_total=suppressions_total,
        emails_last_7_days=emails_last_7_days,
        recent_signups=[RecentSignup.model_validate(u) for u in recent],
    )


# -----------------------------------------------------------------------------
# Users
# -----------------------------------------------------------------------------
@router.get("/users", response_model=AdminUsersResponse)
async def list_users(
    db: DBSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=191),
    role: Optional[str] = Query(None, pattern="^(admin|user)$"),
    is_active: Optional[bool] = Query(None),
    billing_status: Optional[str] = Query(None, max_length=50),
):
    """Paginated user list with search, filters and per-user usage counts."""
    conditions = []
    if search:
        like = f"%{search}%"
        conditions.append(or_(User.email.ilike(like), User.name.ilike(like)))
    if role:
        conditions.append(User.role == role)
    if is_active is not None:
        conditions.append(User.is_active.is_(is_active))
    if billing_status:
        conditions.append(User.billing_status == billing_status)

    total = await _count(db, User, *conditions)

    camp_sq = (
        select(Campaign.user_id, func.count().label("c")).group_by(Campaign.user_id).subquery()
    )
    lead_sq = select(Lead.user_id, func.count().label("c")).group_by(Lead.user_id).subquery()
    mail_sq = (
        select(EmailLog.user_id, func.count().label("c")).group_by(EmailLog.user_id).subquery()
    )

    stmt = (
        select(
            User,
            func.coalesce(camp_sq.c.c, 0).label("campaigns_count"),
            func.coalesce(lead_sq.c.c, 0).label("leads_count"),
            func.coalesce(mail_sq.c.c, 0).label("emails_count"),
        )
        .outerjoin(camp_sq, User.id == camp_sq.c.user_id)
        .outerjoin(lead_sq, User.id == lead_sq.c.user_id)
        .outerjoin(mail_sq, User.id == mail_sq.c.user_id)
        .order_by(User.created_at.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    if conditions:
        stmt = stmt.where(*conditions)

    rows = (await db.execute(stmt)).all()
    items = [
        _to_item(row.User, int(row.campaigns_count), int(row.leads_count), int(row.emails_count))
        for row in rows
    ]
    return AdminUsersResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("/users", response_model=AdminListItem, status_code=status.HTTP_201_CREATED)
async def create_user(payload: AdminUserCreate, db: DBSession, current_admin: CurrentAdmin):
    """Create an account manually (e.g. on behalf of a client)."""
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    user = User(
        email=payload.email,
        name=payload.name,
        role=payload.role,
        password_hash=get_password_hash(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    campaigns, leads, emails = await _usage_counts(db, user.id)
    logger.info("ADMIN %s created user %s (role=%s)", current_admin.email, user.email, user.role)
    return _to_item(user, campaigns, leads, emails)


@router.patch("/users/{user_id}", response_model=AdminListItem)
async def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: DBSession,
    current_admin: CurrentAdmin,
):
    """Partial update: profile, role, active flag, password, billing fields."""
    user = await _get_user_or_404(db, user_id)
    data = payload.model_dump(exclude_unset=True)

    if data.get("role") == "user" and user.role == "admin":
        await _guard_not_self(current_admin, user, "demote")
        await _guard_last_admin(db, user, "demote")
    if data.get("is_active") is False:
        await _guard_not_self(current_admin, user, "deactivate")
        await _guard_last_admin(db, user, "deactivate")

    new_password = data.pop("password", None)
    for field, value in data.items():
        setattr(user, field, value)
    if new_password:
        user.password_hash = get_password_hash(new_password)

    await db.commit()
    await db.refresh(user)
    campaigns, leads, emails = await _usage_counts(db, user.id)
    changed = ", ".join(sorted(data.keys())) or ("password" if new_password else "-")
    logger.info("ADMIN %s updated user %s (fields: %s)", current_admin.email, user.email, changed)
    return _to_item(user, campaigns, leads, emails)


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: DBSession, current_admin: CurrentAdmin):
    """Hard delete. All owned campaigns/leads/emails are removed by DB cascade."""
    user = await _get_user_or_404(db, user_id)
    await _guard_not_self(current_admin, user, "delete")
    await _guard_last_admin(db, user, "delete")

    campaigns, leads, emails = await _usage_counts(db, user.id)
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
    logger.info(
        "ADMIN %s deleted user %s (removed: %s campaigns, %s leads, %s emails)",
        current_admin.email,
        user.email,
        campaigns,
        leads,
        emails,
    )
    return {
        "deleted": True,
        "id": user_id,
        "email": user.email,
        "campaigns_removed": campaigns,
        "leads_removed": leads,
        "emails_removed": emails,
    }


# -----------------------------------------------------------------------------
# System health
# -----------------------------------------------------------------------------
@router.get("/system", response_model=SystemStatus)
async def get_system_status(db: DBSession):
    """
    Liveness of the platform services and which integrations are configured.
    Presence flags only - key values are never returned, and no outbound
    provider API is called (some charge per call).
    """
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    redis_ok = False
    try:
        import redis as redis_lib

        client = redis_lib.Redis.from_url(
            settings.redis_url, socket_connect_timeout=2, socket_timeout=2
        )
        redis_ok = bool(client.ping())
        client.close()
    except Exception:
        pass

    celery_workers: list[str] = []
    try:
        from app.tasks.celery_app import celery_app

        pong = celery_app.control.inspect(timeout=2).ping() or {}
        celery_workers = sorted(pong.keys())
    except Exception:
        pass

    integrations = {
        "serpapi": bool(settings.serpapi_key),
        "gemini": bool(settings.gemini_api_key),
        "openai": bool(settings.openai_api_key),
        "anthropic": bool(settings.anthropic_api_key),
        "smtp": bool(settings.smtp_host and settings.smtp_user),
        "imap": bool(settings.imap_host and settings.imap_user),
    }

    return SystemStatus(
        database=db_ok,
        redis=redis_ok,
        celery_online=bool(celery_workers),
        celery_workers=celery_workers,
        integrations=integrations,
    )

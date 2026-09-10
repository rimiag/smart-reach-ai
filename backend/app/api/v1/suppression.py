"""
Suppression API Endpoints

Manages the per-user suppression list: unsubscribes, bounces and manual
opt-outs. Suppressed emails are skipped before every send.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.dependencies import get_current_user
from app.models.suppression import Suppression
from app.schemas.common import PaginatedResponse
from app.schemas.email import SuppressionAddRequest, SuppressionResponse
from app.schemas.user import UserResponse
from app.services.email_service import email_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse[SuppressionResponse])
async def get_suppression_list(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """List suppressed emails (newest first)."""
    count_query = select(func.count(Suppression.id)).where(Suppression.user_id == current_user.id)
    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        select(Suppression)
        .where(Suppression.user_id == current_user.id)
        .order_by(Suppression.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    entries = result.scalars().all()

    return PaginatedResponse(
        items=[SuppressionResponse.model_validate(s) for s in entries],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.post("", response_model=SuppressionResponse, status_code=status.HTTP_201_CREATED)
async def add_to_suppression(
    payload: SuppressionAddRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Add an email to the suppression list (idempotent)."""
    entry = await email_service.suppress(
        db, current_user.id, payload.email, reason=payload.reason or "manual"
    )
    return SuppressionResponse.model_validate(entry)


@router.delete("/{email}")
async def remove_from_suppression(
    email: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Remove an email from the suppression list (use with care)."""
    entry = await email_service.is_suppressed(db, current_user.id, email)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not suppressed")
    await db.delete(entry)
    await db.commit()
    return {"message": f"{email} removed from suppression list"}

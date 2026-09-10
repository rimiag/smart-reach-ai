"""
Emails API Endpoints

Read access to the outbound email send log (Phase 3). Sending itself happens
through the campaign approval workflow; reply/bounce tracking arrives in
Phase 4.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.dependencies import get_current_user
from app.models.email_log import EmailLog
from app.schemas.common import PaginatedResponse
from app.schemas.email import EmailLogResponse
from app.schemas.user import UserResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[EmailLogResponse])
async def list_emails(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    campaign_id: int = Query(..., description="Campaign ID"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    email_status: str = Query(None, alias="status", description="Filter: sent, failed, bounced"),
):
    """List the campaign's outbound emails (newest first)."""
    query = select(EmailLog).where(
        EmailLog.campaign_id == campaign_id, EmailLog.user_id == current_user.id
    )
    count_query = select(func.count(EmailLog.id)).where(
        EmailLog.campaign_id == campaign_id, EmailLog.user_id == current_user.id
    )
    if email_status:
        query = query.where(EmailLog.status == email_status)
        count_query = count_query.where(EmailLog.status == email_status)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(EmailLog.id.desc()).offset((page - 1) * per_page).limit(per_page)
    )
    emails = result.scalars().all()

    return PaginatedResponse(
        items=[EmailLogResponse.model_validate(e) for e in emails],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.get("/{email_id}", response_model=EmailLogResponse)
async def get_email(
    email_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Get one send-log entry."""
    email = (
        await db.execute(
            select(EmailLog).where(EmailLog.id == email_id, EmailLog.user_id == current_user.id)
        )
    ).scalar_one_or_none()

    if not email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
    return EmailLogResponse.model_validate(email)

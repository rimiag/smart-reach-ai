"""
Replies API Endpoints

The reply inbox (Phase 4): list classified replies, mark them read, and
trigger a mailbox check on demand.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.dependencies import get_current_user
from app.models.reply import Reply
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserResponse
from app.services.reply_monitor import run_reply_check_async

router = APIRouter()


@router.get("/check")
async def trigger_reply_check(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Poll the mailbox now and ingest new replies (same as the periodic beat
    task). Returns the ingest summary.
    """
    return await run_reply_check_async()


@router.get("", response_model=PaginatedResponse)
async def list_replies(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    reply_category: str = Query(None, alias="category"),
    reply_status: str = Query(None, alias="status"),
    campaign_id: int = Query(None),
):
    """List inbound replies (newest first) with optional filters."""
    conditions = [Reply.user_id == current_user.id]
    if reply_category:
        conditions.append(Reply.category == reply_category)
    if reply_status:
        conditions.append(Reply.status == reply_status)
    if campaign_id:
        conditions.append(Reply.campaign_id == campaign_id)

    total = (await db.execute(select(func.count(Reply.id)).where(*conditions))).scalar() or 0

    result = await db.execute(
        select(Reply)
        .where(*conditions)
        .order_by(Reply.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    replies = result.scalars().all()

    return PaginatedResponse(
        items=[
            {
                "id": reply.id,
                "campaign_id": reply.campaign_id,
                "lead_id": reply.lead_id,
                "from_email": reply.from_email,
                "from_name": reply.from_name,
                "subject": reply.subject,
                "body": reply.body,
                "category": reply.category,
                "ai_summary": reply.ai_summary,
                "status": reply.status,
                "received_at": reply.received_at.isoformat() if reply.received_at else None,
                "created_at": reply.created_at.isoformat() if reply.created_at else None,
            }
            for reply in replies
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.patch("/{reply_id}/read")
async def mark_reply_read(
    reply_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Mark a reply as read."""
    reply = (
        await db.execute(
            select(Reply).where(Reply.id == reply_id, Reply.user_id == current_user.id)
        )
    ).scalar_one_or_none()

    if not reply:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reply not found")

    reply.status = "read"
    await db.commit()
    return {"message": "Reply marked as read", "id": reply.id}

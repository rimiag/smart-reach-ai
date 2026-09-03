"""
Analytics API Endpoints

Provides dashboard statistics and campaign analytics (Iteration 1.6).
"""

from typing import Annotated, List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.dependencies import get_current_user
from app.schemas.campaign import CampaignComparison, DashboardStats
from app.schemas.user import UserResponse
from app.services.analytics_service import analytics_service

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Aggregated statistics across all of the current user's campaigns."""
    return await analytics_service.get_dashboard_stats(db, current_user.id)


@router.get("/campaigns", response_model=List[CampaignComparison])
async def get_campaign_analytics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Per-campaign summary rows (newest first) for comparison views."""
    return await analytics_service.get_campaign_comparison(db, current_user.id)


@router.get("/replies")
async def get_reply_analytics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Reply analytics - implemented in Phase 4 (reply detection & classification).
    """
    return {"message": "Reply analytics arrive with Phase 4 (reply detection)"}

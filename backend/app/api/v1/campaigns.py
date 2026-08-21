"""
Campaigns API Endpoints

Handles campaign CRUD, research management, and statistics.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.dependencies import get_current_user
from app.models.campaign import Campaign
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignStats,
    CampaignUpdate,
    ResearchProgress,
)
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserResponse
from app.services.campaign_service import campaign_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse[CampaignResponse])
async def list_campaigns(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """
    List all campaigns for the current user.

    Returns paginated list of campaigns ordered by creation date (newest first).
    """
    skip = (page - 1) * per_page

    campaigns, total = await campaign_service.get_user_campaigns(
        db, current_user.id, skip=skip, limit=per_page
    )

    pages = (total + per_page - 1) // per_page

    return PaginatedResponse(
        items=[CampaignResponse.model_validate(c) for c in campaigns],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Create a new campaign.

    Requires 5-10 keywords for lead generation.
    Campaign is created in 'draft' status.
    """
    new_campaign = await campaign_service.create_campaign(
        db, current_user.id, campaign_data
    )

    return CampaignResponse.model_validate(new_campaign)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Get campaign details by ID.

    Returns full campaign information including keywords and settings.
    """
    campaign = await campaign_service.get_campaign(db, campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Verify ownership
    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign",
        )

    return CampaignResponse.model_validate(campaign)


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    campaign_data: CampaignUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Update campaign details.

    Only campaigns in 'draft' status can be modified.
    """
    campaign = await campaign_service.get_campaign(db, campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Verify ownership
    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this campaign",
        )

    # Check if campaign can be modified
    if campaign.status not in ['draft', 'paused']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify campaign in '{campaign.status}' status",
        )

    updated_campaign = await campaign_service.update_campaign(
        db, campaign, campaign_data
    )

    return CampaignResponse.model_validate(updated_campaign)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Delete a campaign.

    Only campaigns in 'draft' or 'completed' status can be deleted.
    Active campaigns must be paused or completed first.
    """
    campaign = await campaign_service.get_campaign(db, campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Verify ownership
    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this campaign",
        )

    # Check if campaign can be deleted
    if campaign.status in ['researching', 'active']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete active campaign. Pause or complete it first.",
        )

    await campaign_service.delete_campaign(db, campaign)


@router.post("/{campaign_id}/start", response_model=ResearchProgress)
async def start_research(
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Start the research phase for a campaign.

    Initiates web search and crawling based on campaign keywords.
    This will be implemented in Iteration 1.4 with the search agent.
    """
    campaign = await campaign_service.get_campaign(db, campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Verify ownership
    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to start this campaign",
        )

    # Check if campaign is ready to start
    if campaign.status != 'draft':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start campaign in '{campaign.status}' status",
        )

    # TODO: Will be implemented in Iteration 1.4 with Celery tasks
    # For now, just update the status
    updated_campaign = await campaign_service.update_status(
        db, campaign, 'researching'
    )

    return ResearchProgress(
        campaign_id=updated_campaign.id,
        status=updated_campaign.status,
        current_step="Initializing",
        progress_percentage=0.0,
    )


@router.get("/{campaign_id}/progress", response_model=ResearchProgress)
async def get_research_progress(
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Get research progress for a campaign.

    Returns current progress of the research phase including
    websites discovered, crawled, and leads found.
    """
    campaign = await campaign_service.get_campaign(db, campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Verify ownership
    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign",
        )

    # TODO: Will be implemented in Iteration 1.4 with actual progress tracking
    return ResearchProgress(
        campaign_id=campaign.id,
        status=campaign.status,
        current_step="Ready",
        progress_percentage=0.0 if campaign.status == 'draft' else 100.0,
        started_at=campaign.started_at,
    )


@router.get("/{campaign_id}/stats", response_model=CampaignStats)
async def get_campaign_stats(
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Get campaign statistics.

    Returns comprehensive statistics about the campaign including
    websites found, leads created, emails sent, and responses received.
    """
    campaign = await campaign_service.get_campaign(db, campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Verify ownership
    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign",
        )

    # TODO: Will be implemented in Iteration 1.6 with actual stats
    # For now, return empty stats
    return CampaignStats()

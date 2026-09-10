"""
Campaigns API Endpoints

Handles campaign CRUD, research management, and statistics.
"""

import asyncio
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.search_agent import SearchAgent
from app.db.base import get_db
from app.dependencies import get_current_user
from app.integrations.ai_base import AIProviderError, get_ai_client
from app.integrations.search_base import SearchProviderError
from app.integrations.smtp_client import smtp_client
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.research_result import ResearchResult
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignStats,
    CampaignUpdate,
    ResearchProgress,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.campaign import StartResearchRequest
from app.schemas.email import SendRequest
from app.schemas.user import UserResponse
from app.services.analytics_service import analytics_service
from app.services.campaign_service import campaign_service
from app.tasks.progress_tracker import progress_tracker
from app.tasks.search_tasks import run_campaign_search, run_campaign_search_async

logger = logging.getLogger(__name__)

router = APIRouter()

# Keep references to in-process research tasks so they are not garbage
# collected mid-run (laptop-dev fallback when no Redis broker is available).
_background_research_tasks: set = set()


def _dispatch_or_run(celery_task, async_fn, *args) -> MessageResponse:
    """
    Dispatch a task to Celery, falling back to in-process execution when no
    broker is available (local development without Redis).
    """
    try:
        # retry=False: fail fast when no broker is reachable (local dev) so the
        # in-process fallback runs immediately instead of after a ~60s retry.
        celery_task.apply_async(args=list(args), retry=False)
        return MessageResponse(message="Task queued")
    except Exception as exc:
        logger.warning("Celery broker unavailable (%s); running in-process", exc)
        task = asyncio.create_task(async_fn(*args))
        _background_research_tasks.add(task)
        task.add_done_callback(_background_research_tasks.discard)
        return MessageResponse(message="Task started in background")


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
    new_campaign = await campaign_service.create_campaign(db, current_user.id, campaign_data)

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
    if campaign.status not in ["draft", "paused"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify campaign in '{campaign.status}' status",
        )

    updated_campaign = await campaign_service.update_campaign(db, campaign, campaign_data)

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
    if campaign.status in ["researching", "active"]:
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
    payload: Optional[StartResearchRequest] = None,
):
    """
    Start the research phase for a campaign, optionally geo-targeted.

    Body (optional JSON): {"locations": ["United States", ...]} - when set,
    searches are geo-targeted to those locations per keyword.

    Dispatches the search phase (one search-provider query per campaign
    keyword) to the Celery worker. When no message broker is available
    (local development without Redis) the search runs in-process instead.

    Poll ``GET /campaigns/{id}/progress`` for live status.
    """
    locations = [loc.strip() for loc in (payload.locations or []) if loc.strip()] if payload else []

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
    if campaign.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start campaign in '{campaign.status}' status",
        )

    # Fail fast with a clear message when no search provider is configured,
    # instead of letting the background run discover it.
    try:
        SearchAgent()
    except SearchProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # Persist geo-targeting so it's visible/reusable (campaign.settings JSON)
    if locations:
        settings_map = dict(campaign.settings or {})
        settings_map["locations"] = locations
        campaign.settings = settings_map

    updated_campaign = await campaign_service.update_status(db, campaign, "researching")

    # Preferred path: Celery worker on the "search" queue. Fallback: run the
    # same async orchestration in this process (laptop dev without Redis).
    dispatched_via_celery = False
    try:
        # retry=False: fail fast without a broker (local dev) so the
        # in-process fallback starts immediately.
        run_campaign_search.apply_async(
            args=[updated_campaign.id, locations], retry=False
        )
        dispatched_via_celery = True
    except Exception as exc:
        logger.warning(
            "Celery broker unavailable (%s); running campaign %d research in-process",
            exc,
            campaign_id,
        )

    if not dispatched_via_celery:
        research_task = asyncio.create_task(
            run_campaign_search_async(updated_campaign.id, locations)
        )
        _background_research_tasks.add(research_task)
        research_task.add_done_callback(_background_research_tasks.discard)

    progress_tracker.initialize(
        updated_campaign.id,
        keywords_total=len(updated_campaign.keywords or []),
        current_step="Queued",
    )

    return ResearchProgress(
        campaign_id=updated_campaign.id,
        status="researching",
        current_step="Queued",
        progress_percentage=0.0,
        keywords_total=len(updated_campaign.keywords or []),
        keywords_completed=0,
        started_at=updated_campaign.started_at,
    )


@router.get("/{campaign_id}/progress", response_model=ResearchProgress)
async def get_research_progress(
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Get research progress for a campaign.

    Returns live progress from the research tracker (Redis) when a run is
    active; otherwise derives counts from the database.
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

    # Live entry from the tracker (research runs write here).
    tracked = await progress_tracker.get_progress_async(campaign_id)
    if tracked:
        known_fields = ResearchProgress.model_fields.keys()
        return ResearchProgress(**{k: v for k, v in tracked.items() if k in known_fields})

    # Fallback: derive from the database (no active run, or Redis unavailable).
    return await _progress_from_db(db, campaign)


async def _progress_from_db(db: AsyncSession, campaign: Campaign) -> ResearchProgress:
    """Build a ResearchProgress response from stored campaign data."""
    research_total = await db.scalar(
        select(func.count(ResearchResult.id)).where(ResearchResult.campaign_id == campaign.id)
    )
    crawled_total = await db.scalar(
        select(func.count(ResearchResult.id)).where(
            ResearchResult.campaign_id == campaign.id,
            ResearchResult.status == "crawled",
        )
    )
    leads_total = await db.scalar(
        select(func.count(Lead.id)).where(Lead.campaign_id == campaign.id)
    )

    done_statuses = ("ready", "active", "paused", "completed")
    is_done = campaign.status in done_statuses

    return ResearchProgress(
        campaign_id=campaign.id,
        status=campaign.status,
        current_step=("Research complete" if is_done else "Ready to start research"),
        progress_percentage=100.0 if is_done else 0.0,
        websites_found=research_total or 0,
        websites_crawled=crawled_total or 0,
        contacts_found=0,
        leads_created=leads_total or 0,
        keywords_total=len(campaign.keywords or []),
        keywords_completed=len(campaign.keywords or []) if is_done else 0,
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

    # Live statistics from the analytics service (Iteration 1.6)
    return await analytics_service.get_campaign_stats(db, campaign_id)


@router.post("/{campaign_id}/qualify", response_model=MessageResponse)
async def qualify_campaign_leads(
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    AI-qualify the campaign's unscored (``new``) leads.

    Scores each lead 0-100 with reasoning and moves it to ``review`` for the
    human decision queue. Requires an AI provider (ANTHROPIC_API_KEY or
    OPENAI_API_KEY).
    """
    campaign = await campaign_service.get_campaign(db, campaign_id)

    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign",
        )

    try:
        get_ai_client()
    except AIProviderError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    from app.tasks.qualify_tasks import qualify_campaign, run_campaign_qualification_async

    return _dispatch_or_run(qualify_campaign, run_campaign_qualification_async, campaign_id)


@router.post("/{campaign_id}/generate-emails", response_model=MessageResponse)
async def generate_campaign_email_drafts(
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Generate personalized outreach email drafts for the campaign's
    review-ready leads (leads without an existing draft first).
    """
    campaign = await campaign_service.get_campaign(db, campaign_id)

    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign",
        )

    try:
        get_ai_client()
    except AIProviderError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    from app.tasks.email_tasks import generate_campaign_emails, run_campaign_email_generation_async

    return _dispatch_or_run(
        generate_campaign_emails, run_campaign_email_generation_async, campaign_id
    )


@router.post("/{campaign_id}/generate-followups", response_model=MessageResponse)
async def generate_followup_drafts(
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    AI-draft follow-up emails for this campaign's silent leads (sent but no
    reply after the configured window). Drafts land in the review queue for
    human approval before sending.
    """
    campaign = await campaign_service.get_campaign(db, campaign_id)

    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign",
        )

    try:
        get_ai_client()
    except AIProviderError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    from app.tasks.followup_tasks import followup_sweep, run_followup_sweep_async

    return _dispatch_or_run(followup_sweep, run_followup_sweep_async, campaign_id)


@router.post("/{campaign_id}/approve-all", response_model=MessageResponse)
async def approve_all_reviewed_leads(
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Approve every reviewed lead of this campaign that has an email draft -
    the one-click step before starting a send.
    """
    campaign = await campaign_service.get_campaign(db, campaign_id)

    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign",
        )

    leads = (
        (
            await db.execute(
                select(Lead)
                .where(Lead.campaign_id == campaign_id)
                .where(Lead.status == "review")
                .where(Lead.generated_email.is_not(None))
            )
        )
        .scalars()
        .all()
    )

    from datetime import datetime

    for lead in leads:
        lead.status = "approved"
        lead.approved_at = datetime.utcnow()
    await db.commit()

    return MessageResponse(message=f"{len(leads)} lead(s) approved for sending")


@router.post("/{campaign_id}/send", response_model=MessageResponse)
async def send_campaign_emails(
    campaign_id: int,
    payload: SendRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Start sending approved outreach emails for this campaign.

    Explicit human action: only leads you approved (with email drafts) are
    sent, respecting suppression, cooldowns and daily/hourly limits.
    """
    campaign = await campaign_service.get_campaign(db, campaign_id)

    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign",
        )

    if not smtp_client.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP is not configured - set SMTP_HOST, SMTP_USER and SMTP_PASSWORD",
        )

    ready = await db.scalar(
        select(func.count(Lead.id)).where(
            Lead.campaign_id == campaign_id,
            Lead.status == "approved",
            Lead.generated_email.is_not(None),
        )
    )
    if not ready:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No approved leads with email drafts - approve leads first",
        )

    # Remember the sender identity for the next send (prefill in the UI).
    settings_map = dict(campaign.settings or {})
    settings_map.update(
        {
            "sender_name": payload.sender_name,
            "sender_company": payload.sender_company,
            "from_email": str(payload.from_email),
            "reply_to": str(payload.reply_to) if payload.reply_to else "",
        }
    )
    campaign.settings = settings_map
    campaign.status = "active"
    await db.commit()

    from app.tasks.send_tasks import send_campaign_emails as send_task

    dispatch = _dispatch_or_run(
        send_task,
        _send_campaign_runner,
        campaign_id,
        payload.sender_name,
        payload.sender_company,
        str(payload.from_email),
        str(payload.reply_to or ""),
    )
    return MessageResponse(
        message=f"{dispatch.message} - sending {ready} approved email(s) from "
        f"{payload.sender_name} <{payload.from_email}>"
    )


async def _send_campaign_runner(
    campaign_id: int, sender_name: str, sender_company: str, from_email: str, reply_to: str
):
    """In-process fallback runner (matches the Celery task signature)."""
    from app.services.email_service import email_service

    return await email_service.send_campaign(
        campaign_id,
        sender_name=sender_name,
        sender_company=sender_company,
        from_email=from_email,
        reply_to=reply_to,
    )

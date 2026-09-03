"""
Leads API Endpoints

Handles lead management, approval, rejection, and bulk operations.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import get_db
from app.dependencies import get_current_user
from app.models.lead import Lead
from app.schemas.common import BulkActionRequest, PaginatedResponse
from app.schemas.lead import (
    BulkActionResponse,
    LeadActionResponse,
    LeadCreate,
    LeadDetailResponse,
    LeadFilter,
    LeadResponse,
    LeadUpdate,
)
from app.schemas.user import UserResponse
from app.services.campaign_service import campaign_service
from app.services.export_service import export_service
from app.services.lead_service import lead_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse[LeadResponse])
async def list_leads(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    campaign_id: int = Query(..., description="Campaign ID"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str = Query(None, description="Filter by status"),
    min_score: int = Query(None, ge=0, le=100, description="Minimum lead score"),
    max_score: int = Query(None, ge=0, le=100, description="Maximum lead score"),
):
    """
    List leads for a campaign with filtering and pagination.

    Returns paginated list of leads filtered by status and score range.
    """
    skip = (page - 1) * per_page

    leads, total = await lead_service.get_campaign_leads(
        db,
        campaign_id=campaign_id,
        user_id=current_user.id,
        skip=skip,
        limit=per_page,
        status=status,
        min_score=min_score,
        max_score=max_score,
    )

    pages = (total + per_page - 1) // per_page

    return PaginatedResponse(
        items=[LeadResponse.model_validate(lead) for lead in leads],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_data: LeadCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Create a new lead.

    Typically used by the crawler/agent system when discovering contacts.
    Requires a valid campaign_id.
    """
    # Verify campaign ownership
    from sqlalchemy import select

    from app.models.campaign import Campaign

    result = await db.execute(
        select(Campaign).where(
            Campaign.id == lead_data.campaign_id, Campaign.user_id == current_user.id
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found or not authorized",
        )

    new_lead = await lead_service.create_lead(db, current_user.id, lead_data)

    return LeadResponse.model_validate(new_lead)


@router.get("/export")
async def export_leads(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    campaign_id: int = Query(..., description="Campaign ID"),
    format: str = Query("csv", description="Export format: csv, excel or json"),
    lead_status: str = Query(None, alias="status", description="Filter by lead status"),
    min_score: int = Query(None, ge=0, le=100, description="Minimum lead score"),
    max_score: int = Query(None, ge=0, le=100, description="Maximum lead score"),
):
    """
    Export a campaign's leads as CSV, Excel or JSON.

    Returns a file download (Content-Disposition attachment). Optional status
    and score filters mirror the leads list endpoint.
    """
    campaign = await campaign_service.get_campaign(db, campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to export this campaign's leads",
        )

    leads, _total = await lead_service.get_campaign_leads(
        db,
        campaign_id=campaign_id,
        user_id=current_user.id,
        skip=0,
        limit=settings.max_export_size,
        status=lead_status,
        min_score=min_score,
        max_score=max_score,
    )

    try:
        content, media_type, filename = export_service.export(leads, format)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{lead_id}", response_model=LeadDetailResponse)
async def get_lead(
    lead_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Get lead details by ID.

    Returns full lead information including campaign name.
    """
    lead = await lead_service.get_lead(db, lead_id)

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    # Verify ownership
    if lead.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this lead",
        )

    # Validate against LeadResponse first (which doesn't require campaign_name)
    lead_data = LeadResponse.model_validate(lead).model_dump()

    # Add campaign_name and create LeadDetailResponse
    return LeadDetailResponse(
        **lead_data, campaign_name=lead.campaign.name if lead.campaign else "Unknown"
    )


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: int,
    lead_data: LeadUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Update lead details.

    Allows updating contact information and notes.
    """
    lead = await lead_service.get_lead(db, lead_id)

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    # Verify ownership
    if lead.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this lead",
        )

    updated_lead = await lead_service.update_lead(db, lead, lead_data)

    return LeadResponse.model_validate(updated_lead)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Delete a lead.

    Permanently removes the lead from the database.
    """
    lead = await lead_service.get_lead(db, lead_id)

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    # Verify ownership
    if lead.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this lead",
        )

    await lead_service.delete_lead(db, lead)


@router.post("/{lead_id}/approve", response_model=LeadActionResponse)
async def approve_lead(
    lead_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Approve a lead for outreach.

    Changes lead status to 'approved' and sets approval timestamp.
    """
    lead = await lead_service.get_lead(db, lead_id)

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    # Verify ownership
    if lead.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to approve this lead",
        )

    # Check if lead can be approved
    if lead.status in ["approved", "rejected", "sent"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve lead in '{lead.status}' status",
        )

    approved_lead = await lead_service.approve_lead(db, lead)

    return LeadActionResponse(
        id=approved_lead.id, status=approved_lead.status, message="Lead approved successfully"
    )


@router.post("/{lead_id}/reject", response_model=LeadActionResponse)
async def reject_lead(
    lead_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Reject a lead.

    Changes lead status to 'rejected'.
    """
    lead = await lead_service.get_lead(db, lead_id)

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    # Verify ownership
    if lead.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to reject this lead",
        )

    # Check if lead can be rejected
    if lead.status in ["approved", "rejected", "sent"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject lead in '{lead.status}' status",
        )

    rejected_lead = await lead_service.reject_lead(db, lead)

    return LeadActionResponse(
        id=rejected_lead.id, status=rejected_lead.status, message="Lead rejected successfully"
    )


@router.post("/bulk-approve", response_model=BulkActionResponse)
async def bulk_approve_leads(
    action_data: BulkActionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Bulk approve multiple leads.

    Processes approval for all provided lead IDs that belong to the user
    and are in an approvable state.
    """
    result = await lead_service.bulk_approve(db, action_data.ids, current_user.id)

    message = f"Approved {result['success_count']} leads"
    if result["failed_count"] > 0:
        message += f", {result['failed_count']} failed"

    return BulkActionResponse(
        success_count=result["success_count"],
        failed_count=result["failed_count"],
        errors=result["errors"],
        message=message,
    )


@router.post("/bulk-reject", response_model=BulkActionResponse)
async def bulk_reject_leads(
    action_data: BulkActionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Bulk reject multiple leads.

    Processes rejection for all provided lead IDs that belong to the user
    and are in a rejectable state.
    """
    result = await lead_service.bulk_reject(db, action_data.ids, current_user.id)

    message = f"Rejected {result['success_count']} leads"
    if result["failed_count"] > 0:
        message += f", {result['failed_count']} failed"

    return BulkActionResponse(
        success_count=result["success_count"],
        failed_count=result["failed_count"],
        errors=result["errors"],
        message=message,
    )

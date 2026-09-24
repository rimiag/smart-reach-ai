"""
Leads API Endpoints

Handles lead management, approval, rejection, and bulk operations.
"""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.email_agent import EmailGenerationAgent, EmailParseError
from app.agents.qualification_agent import QualificationAgent, QualificationParseError
from app.core.config import settings
from app.db.base import get_db
from app.dependencies import get_current_user, hold_guard
from app.integrations.ai_base import AIProviderError
from app.integrations.smtp_client import SMTPSendError, smtp_client
from app.models.campaign import Campaign
from app.models.email_log import EmailLog
from app.models.lead import Lead
from app.schemas.common import BulkActionRequest, PaginatedResponse
from app.schemas.lead import (
    BulkActionResponse,
    LeadActionResponse,
    LeadCreate,
    LeadDetailResponse,
    LeadDraftUpdate,
    LeadFilter,
    LeadManualEmail,
    LeadResponse,
    LeadUpdate,
)
from app.schemas.user import UserResponse
from app.services.campaign_service import campaign_service
from app.services.email_service import UNSUBSCRIBE_FOOTER, email_service
from app.services.export_service import export_service
from app.services.lead_service import lead_service
from app.services.template_service import template_service

router = APIRouter(dependencies=[Depends(hold_guard)])


@router.get("", response_model=PaginatedResponse[LeadResponse])
async def list_leads(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    campaign_id: Optional[int] = Query(
        None, description="Campaign ID (omit to list leads across all your campaigns)"
    ),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str = Query(None, description="Filter by status"),
    min_score: int = Query(None, ge=0, le=100, description="Minimum lead score"),
    max_score: int = Query(None, ge=0, le=100, description="Maximum lead score"),
):
    """
    List leads with filtering and pagination.

    Pass campaign_id to list one campaign's leads (the leads page), or omit it
    to list every lead the user owns across campaigns (dashboard Leads tab).
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


async def _get_owned_lead(lead_id: int, db: AsyncSession, current_user: UserResponse) -> Lead:
    """Load a lead with its campaign and verify ownership (404/403 on failure)."""
    lead = await lead_service.get_lead(db, lead_id)

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    if lead.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this lead",
        )

    return lead


@router.put("/{lead_id}/draft", response_model=LeadResponse)
async def update_lead_draft(
    lead_id: int,
    draft_data: LeadDraftUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Edit a lead's email draft (subject and body).

    Allowed while the lead is in ``review`` or ``approved`` status, so drafts
    stay editable right up until they are sent.
    """
    lead = await _get_owned_lead(lead_id, db, current_user)

    if lead.status not in ("review", "approved"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Drafts can only be edited for leads in review or approved "
            f"status (current: {lead.status})",
        )

    subject = draft_data.subject.strip()
    body = draft_data.body.strip()
    if not subject or not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subject and body must not be empty",
        )

    lead.generated_email = f"Subject: {subject}\n\n{body}"
    await db.commit()
    await db.refresh(lead)

    return LeadResponse.model_validate(lead)


@router.post("/{lead_id}/qualify", response_model=LeadResponse)
async def qualify_lead(
    lead_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    AI-qualify a single lead: score 0-100 with reasoning and move it to
    ``review``. Requires an AI provider to be configured.
    """
    lead = await _get_owned_lead(lead_id, db, current_user)

    try:
        agent = QualificationAgent()
    except AIProviderError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    try:
        result = await agent.qualify(lead, lead.campaign)
    except (AIProviderError, QualificationParseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI qualification failed: {exc}",
        )

    lead.lead_score = result.score
    reasoning = f"[{result.category}] {result.reasoning}" if result.category else result.reasoning
    if result.signals:
        reasoning += f" | Signals: {', '.join(result.signals)}"
    lead.ai_reasoning = reasoning
    lead.status = "review"
    lead.qualified_at = datetime.utcnow()
    await db.commit()
    await db.refresh(lead)

    return LeadResponse.model_validate(lead)


@router.post("/{lead_id}/regenerate", response_model=LeadResponse)
async def regenerate_lead_email(
    lead_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Generate (or regenerate) the personalized outreach email draft for a
    single lead. Requires an AI provider to be configured.
    """
    lead = await _get_owned_lead(lead_id, db, current_user)

    try:
        agent = EmailGenerationAgent()
    except AIProviderError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    template_hint = template_service.render(
        template_service.get_template("professional"),
        {"ORGANIZATION_NAME": lead.organization_name},
    )

    try:
        draft = await agent.generate(lead, lead.campaign, template_hint=template_hint)
    except (AIProviderError, EmailParseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI email generation failed: {exc}",
        )

    lead.generated_email = f"Subject: {draft.subject}\n\n{draft.body}"
    await db.commit()
    await db.refresh(lead)

    return LeadResponse.model_validate(lead)


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: int,
    lead_data: LeadUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Update lead details.

    Allows updating contact information, notes, and re-assigning the lead to
    another campaign.
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

    # Campaign assignment: the target campaign must belong to the user
    if lead_data.campaign_id is not None and lead_data.campaign_id != lead.campaign_id:
        result = await db.execute(
            select(Campaign).where(
                Campaign.id == lead_data.campaign_id, Campaign.user_id == current_user.id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target campaign not found or not authorized",
            )

    updated_lead = await lead_service.update_lead(db, lead, lead_data)

    return LeadResponse.model_validate(updated_lead)


@router.post("/{lead_id}/email", response_model=LeadActionResponse)
async def email_lead(
    lead_id: int,
    email_data: LeadManualEmail,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Manually email a single lead straight from the app.

    Explicit human action: sends immediately, appends the standard unsubscribe
    footer, and logs the attempt to the emails table so the mailbox thread,
    reply matching and email stats keep working. Suppressed and
    do-not-contact leads are refused. Unlike bulk campaign sends there is no
    cooldown check - re-emailing a lead manually is intentionally allowed.
    """
    lead = await _get_owned_lead(lead_id, db, current_user)

    if not lead.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This lead has no email address",
        )
    if lead.do_not_contact:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This lead is marked do-not-contact",
        )
    if not smtp_client.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP is not configured - set SMTP_HOST, SMTP_USER and SMTP_PASSWORD",
        )

    suppression = await email_service.is_suppressed(db, current_user.id, lead.email)
    if suppression is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This email is on your suppression list (reason: {suppression.reason})",
        )

    subject = email_data.subject.strip()
    body = email_data.body.strip()
    if not subject or not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subject and body must not be empty",
        )

    # Sender identity: explicit override > the identity the campaign was last
    # sent from (same rule as mailbox replies) > the SMTP default user.
    last_out = (
        (
            await db.execute(
                select(EmailLog)
                .where(EmailLog.lead_id == lead.id)
                .order_by(EmailLog.id.desc())
            )
        )
        .scalars()
        .first()
    )
    campaign_settings = dict(lead.campaign.settings or {}) if lead.campaign else {}
    from_email = (
        email_data.from_email or (last_out.from_email if last_out else "") or settings.smtp_user
    )
    if not from_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No sender address available - set SMTP_USER or pass from_email",
        )
    from_name = email_data.from_name or current_user.name or "ReachPulse"
    reply_to = campaign_settings.get("reply_to") or from_email

    # Same compliance footer the bulk campaign sends append.
    final_body = f"{body}{UNSUBSCRIBE_FOOTER.format(unsubscribe_url=email_service.unsubscribe_url(lead))}"

    try:
        sent = await smtp_client.send(
            from_addr=from_email,
            from_name=from_name,
            to_addr=lead.email,
            subject=subject,
            body=final_body,
            reply_to=reply_to,
        )
    except SMTPSendError as exc:
        db.add(
            EmailLog(
                campaign_id=lead.campaign_id,
                lead_id=lead.id,
                user_id=current_user.id,
                to_email=lead.email,
                from_email=from_email,
                subject=subject,
                body=final_body,
                status="failed",
                provider="smtp",
                error_message=str(exc)[:500],
                unsubscribe_token=email_service.unsubscribe_token(lead),
            )
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Email send failed: {exc}",
        )

    db.add(
        EmailLog(
            campaign_id=lead.campaign_id,
            lead_id=lead.id,
            user_id=current_user.id,
            to_email=lead.email,
            from_email=from_email,
            subject=subject,
            body=final_body,
            status="sent",
            provider="smtp",
            message_id=sent.message_id,
            unsubscribe_token=email_service.unsubscribe_token(lead),
            sent_at=datetime.utcnow(),
        )
    )
    lead.emails_sent = (lead.emails_sent or 0) + 1
    lead.last_emailed_at = datetime.utcnow()
    # Advance the pipeline only forward - never downgrade replied/interested.
    if lead.status in ("new", "researching", "qualified", "review", "approved", "scheduled"):
        lead.status = "sent"
    await db.commit()
    await db.refresh(lead)

    return LeadActionResponse(
        id=lead.id, status=lead.status, message=f"Email sent to {lead.email}"
    )


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

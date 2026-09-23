"""
Mailbox

Threaded view of one lead conversation (our outreach + their replies) and
the ability to answer a reply directly. Replies go out through the same SMTP
identity the campaign was sent from, with In-Reply-To/References headers so
mail clients thread them into the original conversation.
"""

import logging
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.config import settings
from app.dependencies import DBSession, get_current_user, hold_guard
from app.integrations.smtp_client import SMTPSendError, smtp_client
from app.models.campaign import Campaign
from app.models.email_log import EmailLog
from app.models.lead import Lead
from app.models.reply import Reply
from app.schemas.user import UserResponse

router = APIRouter(dependencies=[Depends(hold_guard)])

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
class MailboxMessageOut(BaseModel):
    """One message in a conversation (in = from the lead, out = ours)."""

    direction: str
    subject: Optional[str] = None
    body: str
    from_email: str = ""
    to_email: Optional[str] = None
    at: Optional[datetime] = None
    status: Optional[str] = None
    category: Optional[str] = None
    ai_summary: Optional[str] = None


class MailboxThreadOut(BaseModel):
    """Conversation summary for the list pane."""

    lead_id: int
    campaign_id: int
    campaign_name: Optional[str] = None
    lead_name: Optional[str] = None
    email: Optional[str] = None
    last_direction: Optional[str] = None
    last_subject: Optional[str] = None
    last_preview: str = ""
    last_at: Optional[datetime] = None
    unread_count: int = 0
    total_count: int = 0


class MailboxThreadsResponse(BaseModel):
    items: List[MailboxThreadOut]
    total: int


class MailboxThreadDetail(BaseModel):
    lead_id: int
    lead_name: Optional[str] = None
    email: Optional[str] = None
    campaign_id: int
    campaign_name: Optional[str] = None
    messages: List[MailboxMessageOut]


class MailboxReplyRequest(BaseModel):
    lead_id: int
    body: str = Field(..., min_length=1, max_length=20000)
    subject: Optional[str] = Field(None, max_length=255)


class MailboxReplyOut(BaseModel):
    """The message as stored, so the UI can append it to the thread."""

    message: MailboxMessageOut


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _out_at(email_row: EmailLog) -> Optional[datetime]:
    return email_row.sent_at or email_row.created_at


def _in_at(reply_row: Reply) -> Optional[datetime]:
    return reply_row.received_at or reply_row.created_at


def _preview(text: str, limit: int = 120) -> str:
    collapsed = " ".join((text or "").split())
    return collapsed[:limit] + ("..." if len(collapsed) > limit else "")


async def _owned_lead(db, lead_id: int, user_id: int) -> Lead:
    lead = (
        await db.execute(select(Lead).where(Lead.id == lead_id, Lead.user_id == user_id))
    ).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


async def _campaign_names(db, campaign_ids) -> dict:
    ids = {c for c in campaign_ids if c}
    if not ids:
        return {}
    rows = (await db.execute(select(Campaign).where(Campaign.id.in_(ids)))).scalars().all()
    return {c.id: c.name for c in rows}


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.get("/threads", response_model=MailboxThreadsResponse)
async def list_threads(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: DBSession,
    campaign_id: int = Query(None, description="Only threads for this campaign"),
    unread_only: bool = Query(False, description="Only threads with unread replies"),
):
    """One conversation per lead that has outreach and/or replies."""
    emails = (
        await db.execute(select(EmailLog).where(EmailLog.user_id == current_user.id))
    ).scalars().all()
    replies = (
        await db.execute(select(Reply).where(Reply.user_id == current_user.id))
    ).scalars().all()

    lead_ids = {e.lead_id for e in emails} | {r.lead_id for r in replies}
    leads = {}
    if lead_ids:
        rows = (
            await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
        ).scalars().all()
        leads = {l.id: l for l in rows}

    threads = {}

    def _thread_for(lead_id: int) -> MailboxThreadOut:
        if lead_id not in threads:
            lead = leads.get(lead_id)
            threads[lead_id] = MailboxThreadOut(
                lead_id=lead_id,
                campaign_id=lead.campaign_id if lead else 0,
                lead_name=lead.organization_name if lead else None,
                email=lead.email if lead else None,
            )
        return threads[lead_id]

    for e in emails:
        t = _thread_for(e.lead_id)
        at = _out_at(e)
        t.total_count += 1
        if t.last_at is None or (at and at >= t.last_at):
            t.last_direction = "out"
            t.last_subject = e.subject
            t.last_preview = _preview(e.body)
            t.last_at = at

    for r in replies:
        t = _thread_for(r.lead_id)
        at = _in_at(r)
        t.total_count += 1
        if r.status == "unread":
            t.unread_count += 1
        if t.last_at is None or (at and at >= t.last_at):
            t.last_direction = "in"
            t.last_subject = r.subject
            t.last_preview = _preview(r.body)
            t.last_at = at

    names = await _campaign_names(db, {t.campaign_id for t in threads.values()})
    items = [t for t in threads.values() if t.campaign_id != 0]
    for t in items:
        t.campaign_name = names.get(t.campaign_id)

    if campaign_id is not None:
        items = [t for t in items if t.campaign_id == campaign_id]
    if unread_only:
        items = [t for t in items if t.unread_count > 0]

    items.sort(key=lambda t: t.last_at or datetime.min, reverse=True)
    return MailboxThreadsResponse(items=items, total=len(items))


@router.get("/threads/{lead_id}", response_model=MailboxThreadDetail)
async def get_thread(
    lead_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: DBSession,
):
    """Full conversation with one lead, oldest to newest."""
    lead = await _owned_lead(db, lead_id, current_user.id)

    emails = (
        await db.execute(
            select(EmailLog)
            .where(EmailLog.lead_id == lead_id, EmailLog.user_id == current_user.id)
            .order_by(EmailLog.created_at)
        )
    ).scalars().all()
    replies = (
        await db.execute(
            select(Reply)
            .where(Reply.lead_id == lead_id, Reply.user_id == current_user.id)
            .order_by(Reply.created_at)
        )
    ).scalars().all()

    messages = [
        MailboxMessageOut(
            direction="out",
            subject=e.subject,
            body=e.body,
            from_email=e.from_email,
            to_email=e.to_email,
            at=_out_at(e),
            status=e.status,
        )
        for e in emails
    ]
    messages += [
        MailboxMessageOut(
            direction="in",
            subject=r.subject,
            body=r.body,
            from_email=r.from_email,
            to_email=lead.email,
            at=_in_at(r),
            status=r.status,
            category=r.category,
            ai_summary=r.ai_summary,
        )
        for r in replies
    ]
    messages.sort(key=lambda m: m.at or datetime.min)

    names = await _campaign_names(db, {lead.campaign_id})
    return MailboxThreadDetail(
        lead_id=lead.id,
        lead_name=lead.organization_name,
        email=lead.email,
        campaign_id=lead.campaign_id,
        campaign_name=names.get(lead.campaign_id),
        messages=messages,
    )


@router.post("/reply", response_model=MailboxReplyOut)
async def reply_to_lead(
    payload: MailboxReplyRequest,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: DBSession,
):
    """Answer a lead from the mailbox (threaded via In-Reply-To)."""
    lead = await _owned_lead(db, payload.lead_id, current_user.id)
    if not lead.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This lead has no email address to reply to.",
        )

    last_out = (
        await db.execute(
            select(EmailLog)
            .where(EmailLog.lead_id == lead.id, EmailLog.user_id == current_user.id)
            .order_by(EmailLog.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    last_in = (
        await db.execute(
            select(Reply)
            .where(Reply.lead_id == lead.id, Reply.user_id == current_user.id)
            .order_by(Reply.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    # Send from the identity the campaign used so the thread stays consistent
    from_email = (last_out.from_email if last_out else "") or settings.smtp_user
    if not from_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No sending identity found - send the campaign first or set SMTP_USER.",
        )
    from_name = current_user.name or "ReachPulse"

    # Reference the newest message we have headers for, preferring the lead's
    # own Message-ID so their mail client threads our answer under their mail.
    if last_in is not None:
        thread_id = last_in.message_id or last_in.in_reply_to or (
            last_out.message_id if last_out else ""
        )
    else:
        thread_id = last_out.message_id if last_out else ""

    if payload.subject:
        subject = payload.subject
    elif last_in is not None and last_in.subject:
        subject = (
            last_in.subject
            if last_in.subject.startswith("Re:")
            else f"Re: {last_in.subject}"
        )
    elif last_out is not None and last_out.subject:
        subject = f"Re: {last_out.subject}"
    else:
        subject = f"Follow-up from {from_name}"

    try:
        sent = await smtp_client.send(
            from_addr=from_email,
            from_name=from_name,
            to_addr=lead.email,
            subject=subject,
            body=payload.body,
            in_reply_to=thread_id,
        )
    except SMTPSendError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    now = datetime.utcnow()
    log = EmailLog(
        campaign_id=lead.campaign_id,
        lead_id=lead.id,
        user_id=current_user.id,
        to_email=lead.email,
        from_email=from_email,
        subject=subject[:255],
        body=payload.body,
        status="sent",
        provider="smtp",
        message_id=sent.message_id,
        sent_at=now,
    )
    db.add(log)
    if last_in is not None and last_in.status == "unread":
        last_in.status = "read"
    await db.commit()

    logger.info(
        "Mailbox reply sent to %s (lead %s, message-id=%s)",
        lead.email,
        lead.id,
        sent.message_id,
    )
    return MailboxReplyOut(
        message=MailboxMessageOut(
            direction="out",
            subject=log.subject,
            body=log.body,
            from_email=from_email,
            to_email=lead.email,
            at=now,
            status="sent",
        )
    )

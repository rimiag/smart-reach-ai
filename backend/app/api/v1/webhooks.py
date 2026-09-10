"""
Webhook API Endpoints

Generic inbound webhook (Phase 4) so external systems - email parsing
services, provider webhooks, or manual integrations - can push replies into
the same classification pipeline as the IMAP poller.

Optional shared-secret auth: when ``WEBHOOK_SECRET`` is set, callers must send
``X-Webhook-Secret``.
"""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.integrations.imap_client import RawReply
from app.services.reply_monitor import ReplyMonitor

router = APIRouter()


class InboundReplyPayload(BaseModel):
    """Generic inbound reply pushed by an external system."""

    from_email: str = Field(..., description="Sender address")
    subject: str = Field(default="", description="Reply subject")
    body: str = Field(..., description="Reply body text")
    from_name: str = Field(default="", description="Sender display name")
    message_id: str = Field(default="", description="Message-ID this reply references")
    received_at: Optional[datetime] = Field(default=None, description="Received timestamp")


@router.post("/reply")
async def receive_reply(
    payload: InboundReplyPayload,
    x_webhook_secret: Annotated[
        Optional[str], Header(description="Shared secret when WEBHOOK_SECRET is configured")
    ] = None,
):
    """
    Ingest one inbound reply through the standard matching + classification
    pipeline (thread match by message_id, then sender-address fallback).
    """
    from app.core.config import settings
    from app.db.base import AsyncSessionLocal

    if settings.webhook_secret and x_webhook_secret != settings.webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret"
        )

    raw = RawReply(
        from_email=payload.from_email.strip().lower(),
        from_name=payload.from_name,
        subject=payload.subject,
        body=payload.body,
        in_reply_to=payload.message_id,
        received_at=payload.received_at,
    )

    monitor = ReplyMonitor()
    summary = await monitor.ingest_replies([raw])

    if summary.get("matched"):
        return {"status": "ingested", "category": next(iter(summary.get("by_category", {})), None)}
    return {"status": "ignored", "reason": "no matching lead for this sender"}

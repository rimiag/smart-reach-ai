"""
Email Schemas

Response/request models for the send log (Phase 3).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SendRequest(BaseModel):
    """Human-approved campaign send request."""

    sender_name: str = Field(..., min_length=1, max_length=100, description="Your name")
    sender_company: str = Field(default="", max_length=100, description="Your company")
    from_email: EmailStr = Field(
        ..., description="From address (must be allowed by the SMTP provider)"
    )
    reply_to: Optional[EmailStr] = Field(default=None, description="Optional Reply-To address")


class EmailLogResponse(BaseModel):
    """One outbound email from the send log."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    lead_id: int
    to_email: str
    from_email: str
    subject: str
    status: str
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime


class SuppressionResponse(BaseModel):
    """One suppression entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    reason: str
    lead_id: Optional[int] = None
    created_at: datetime


class SuppressionAddRequest(BaseModel):
    """Add an email to the suppression list."""

    email: EmailStr
    reason: str = Field(default="manual", description="manual, unsubscribed or bounced")

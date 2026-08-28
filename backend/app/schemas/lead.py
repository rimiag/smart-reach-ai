"""
Lead Schemas

Pydantic models for lead-related requests and responses.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# Lead status literal type
LeadStatus = Literal[
    "new",
    "researching",
    "qualified",
    "review",
    "approved",
    "rejected",
    "scheduled",
    "sent",
    "replied",
    "interested",
    "not_interested",
    "unsubscribed",
    "bounced",
    "do_not_contact",
]


# -----------------------------------------------------------------------------
# Base Lead Schema
# -----------------------------------------------------------------------------
class LeadBase(BaseModel):
    """Base lead fields."""

    organization_name: str = Field(
        ..., min_length=1, max_length=255, description="Organization name"
    )
    website: str = Field(..., min_length=1, max_length=255, description="Website URL")
    email: Optional[str] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, description="Contact phone number")


# -----------------------------------------------------------------------------
# Request Schemas
# -----------------------------------------------------------------------------
class LeadCreate(LeadBase):
    """Schema for creating a new lead."""

    campaign_id: int = Field(..., description="Campaign ID")
    keyword: str = Field(
        ..., min_length=1, max_length=255, description="Keyword that found this lead"
    )
    source_url: str = Field(..., description="URL where lead was found")
    contact_page_url: Optional[str] = Field(None, description="Contact page URL")
    contact_name: Optional[str] = Field(None, max_length=255, description="Contact person name")
    job_title: Optional[str] = Field(None, max_length=255, description="Contact job title")
    department: Optional[str] = Field(None, max_length=255, description="Contact department")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    city: Optional[str] = Field(None, max_length=100, description="City")
    lead_score: int = Field(default=0, ge=0, le=100, description="AI lead score (0-100)")
    ai_reasoning: Optional[str] = Field(None, description="AI qualification reasoning")


class LeadUpdate(BaseModel):
    """Schema for updating lead details."""

    organization_name: Optional[str] = Field(None, min_length=1, max_length=255)
    website: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_name: Optional[str] = Field(None, max_length=255)
    job_title: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=255)
    country: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, description="Additional notes")


class BulkActionRequest(BaseModel):
    """Schema for bulk operations on leads."""

    ids: list[int] = Field(..., min_length=1, description="List of lead IDs")


# -----------------------------------------------------------------------------
# Response Schemas
# -----------------------------------------------------------------------------
class LeadResponse(LeadBase):
    """Schema for lead response."""

    id: int
    campaign_id: int
    keyword: str
    source_url: str
    contact_page_url: Optional[str] = None
    contact_name: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    lead_score: int
    ai_reasoning: Optional[str] = None
    status: LeadStatus
    generated_email: Optional[str] = None
    emails_sent: int
    last_emailed_at: Optional[datetime] = None
    do_not_contact: bool
    unsubscribed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    qualified_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LeadDetailResponse(LeadResponse):
    """Extended lead response with campaign information."""

    campaign_name: str = Field(..., description="Associated campaign name")


# -----------------------------------------------------------------------------
# Action Response Schemas
# -----------------------------------------------------------------------------
class LeadActionResponse(BaseModel):
    """Response for lead action (approve/reject)."""

    id: int
    status: LeadStatus
    message: str


class BulkActionResponse(BaseModel):
    """Response for bulk operations."""

    success_count: int
    failed_count: int
    errors: list[str] = []
    message: str


# -----------------------------------------------------------------------------
# Filter Schemas
# -----------------------------------------------------------------------------
class LeadFilter(BaseModel):
    """Schema for lead filtering."""

    status: Optional[LeadStatus] = None
    campaign_id: Optional[int] = None
    min_score: Optional[int] = Field(None, ge=0, le=100)
    max_score: Optional[int] = Field(None, ge=0, le=100)
    has_email: Optional[bool] = None
    keyword: Optional[str] = None

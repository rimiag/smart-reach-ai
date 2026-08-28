"""
Campaign Schemas

Pydantic models for campaign-related requests and responses.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# Campaign status literal type
CampaignStatus = Literal["draft", "researching", "ready", "active", "paused", "completed"]


# -----------------------------------------------------------------------------
# Base Campaign Schema
# -----------------------------------------------------------------------------
class CampaignBase(BaseModel):
    """Base campaign fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Campaign name")
    description: Optional[str] = Field(None, description="Campaign description")


# -----------------------------------------------------------------------------
# Request Schemas
# -----------------------------------------------------------------------------
class CampaignCreate(CampaignBase):
    """Schema for creating a new campaign."""

    keywords: list[str] = Field(
        ...,
        min_length=5,
        max_length=10,
        description="List of keywords (5-10 required)",
    )

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: list[str]) -> list[str]:
        """Validate keywords are non-empty and trimmed."""
        keywords = [k.strip() for k in v if k.strip()]
        if len(keywords) < 5 or len(keywords) > 10:
            raise ValueError("Must have between 5 and 10 keywords")
        return keywords


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    keywords: Optional[list[str]] = Field(None, min_length=5, max_length=10)
    settings: Optional[dict] = None


# -----------------------------------------------------------------------------
# Response Schemas
# -----------------------------------------------------------------------------
class CampaignResponse(CampaignBase):
    """Schema for campaign response."""

    id: int
    user_id: int
    status: CampaignStatus
    keywords: list[str]
    settings: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# -----------------------------------------------------------------------------
# Statistics Schema
# -----------------------------------------------------------------------------
class CampaignStats(BaseModel):
    """Campaign statistics."""

    websites_found: int = 0
    websites_crawled: int = 0
    contacts_found: int = 0
    leads_created: int = 0
    leads_qualified: int = 0
    emails_sent: int = 0
    emails_delivered: int = 0
    emails_opened: int = 0
    replies_received: int = 0
    interested_leads: int = 0
    unsubscribes: int = 0
    bounces: int = 0


# -----------------------------------------------------------------------------
# Research Progress Schema
# -----------------------------------------------------------------------------
class ResearchProgress(BaseModel):
    """Research progress tracking."""

    campaign_id: int
    status: CampaignStatus
    current_step: str
    progress_percentage: float
    websites_found: int = 0
    websites_crawled: int = 0
    contacts_found: int = 0
    leads_created: int = 0
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

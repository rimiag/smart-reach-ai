"""
Contact Info Schema

Normalized contact details extracted from a crawled website (Iteration 1.5).
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    """Public contact details extracted from a website by the crawler."""

    organization_name: Optional[str] = None
    website: str
    contact_name: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    country: Optional[str] = None
    city: Optional[str] = None
    contact_page_url: Optional[str] = None
    source_urls: List[str] = Field(default_factory=list)

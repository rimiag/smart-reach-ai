"""
Duplicate Detector

Prevents the crawler from creating a second lead for the same organization.

An index of domains and emails of the campaign's existing leads is built once
per crawl run, then every candidate is checked in memory.
"""

import logging
from typing import Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.search_base import extract_domain
from app.models.lead import Lead

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """In-memory index of a campaign's existing lead identities."""

    def __init__(self, domains: Set[str], emails: Set[str]) -> None:
        self._domains = domains
        self._emails = emails

    @classmethod
    async def create(cls, db: AsyncSession, campaign_id: int) -> "DuplicateDetector":
        """Build the index from all leads currently stored for the campaign."""
        result = await db.execute(
            select(Lead.website, Lead.email).where(Lead.campaign_id == campaign_id)
        )
        domains: Set[str] = set()
        emails: Set[str] = set()
        for website, email in result.all():
            domain = extract_domain(website or "")
            if domain:
                domains.add(domain)
            if email:
                emails.add(email.strip().lower())
        logger.info(
            "Duplicate index for campaign %d: %d domains, %d emails",
            campaign_id,
            len(domains),
            len(emails),
        )
        return cls(domains, emails)

    def is_duplicate(self, website: str, emails: Tuple[str, ...] = ()) -> bool:
        """Check a candidate website/email set against the index."""
        domain = extract_domain(website or "")
        if domain and domain in self._domains:
            return True
        for email in emails or ():
            if email and email.strip().lower() in self._emails:
                return True
        return False

    def add_identity(self, website: str, emails: Tuple[str, ...] = ()) -> None:
        """Register a newly created lead so later candidates in the same run
        are detected as duplicates of it."""
        domain = extract_domain(website or "")
        if domain:
            self._domains.add(domain)
        for email in emails or ():
            if email:
                self._emails.add(email.strip().lower())

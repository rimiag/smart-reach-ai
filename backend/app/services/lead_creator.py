"""
Lead Creator

Turns normalized crawler output (ContactInfo + the originating ResearchResult)
into a Lead row, reusing the standard lead service for creation.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research_result import ResearchResult
from app.schemas.contact_info import ContactInfo
from app.schemas.lead import LeadCreate
from app.services.lead_service import lead_service

logger = logging.getLogger(__name__)


class LeadCreator:
    """Creates leads from crawler contact extractions."""

    async def create_from_contact_info(
        self,
        db: AsyncSession,
        research_result: ResearchResult,
        contact: ContactInfo,
    ):
        """
        Create a lead from a crawled website's contact info.

        The first discovered email/phone is stored on the lead; the full sets
        remain available in the research result metadata for later iterations.
        """
        lead_data = LeadCreate(
            campaign_id=research_result.campaign_id,
            keyword=research_result.keyword,
            source_url=research_result.url,
            contact_page_url=contact.contact_page_url,
            organization_name=(contact.organization_name or research_result.domain),
            website=contact.website,
            email=contact.emails[0] if contact.emails else None,
            phone=contact.phones[0] if contact.phones else None,
            country=contact.country,
            city=contact.city,
        )
        lead = await lead_service.create_lead(db, research_result.user_id, lead_data)
        logger.info(
            "Lead %d created from %s (%s)",
            lead.id,
            research_result.domain,
            lead.organization_name,
        )
        return lead


lead_creator = LeadCreator()

"""
Personalization Service

Builds the per-lead personalization context (facts the AI may reference) from
the lead and campaign, shared by the email generation agent and any template
rendering.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class PersonalizationService:
    """Extracts personalization facts for email generation."""

    def build_context(self, lead, campaign) -> Dict[str, str]:
        """
        Collect lead + campaign facts for the generation prompt.

        Only verified facts are included - the generation prompt forbids the
        model from inventing anything not present here.
        """
        return {
            "organization_name": lead.organization_name,
            "website": lead.website,
            "contact_name": lead.contact_name or "",
            "job_title": lead.job_title or "",
            "email": lead.email or "",
            "keyword": ", ".join(campaign.keywords or []),
            "campaign_description": campaign.description or "",
            "contact_page_url": lead.contact_page_url or "",
            "ai_reasoning": (lead.ai_reasoning or "")[:300],
        }

    def format_context(self, context: Dict[str, str]) -> str:
        """Render the context dict as readable prompt lines (skipping empties)."""
        labels = {
            "organization_name": "Organization",
            "website": "Website",
            "contact_name": "Contact",
            "job_title": "Job title",
            "email": "Email",
            "keyword": "Campaign keywords",
            "campaign_description": "Campaign goal",
            "contact_page_url": "Contact page",
            "ai_reasoning": "Qualification notes",
        }
        lines = [
            f"{labels[key]}: {value}" for key, value in context.items() if value and labels.get(key)
        ]
        return "\n".join(lines) if lines else "(no personalization data)"


personalization_service = PersonalizationService()

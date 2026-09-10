"""
Template Service

Base outreach email structures used as hints for the email generation agent,
selected round-robin so a campaign's drafts vary in style. Placeholders are
filled at render/send time ({{SENDER_*}} by Phase 3, lead fields by the
personalization service).
"""

import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)

# Style variants from the development plan (lean set; the AI adapts them).
EMAIL_TEMPLATES: Dict[str, str] = {
    "professional": (
        "Hi {{CONTACT_NAME|there}},\n\n"
        "I came across {{ORGANIZATION_NAME}} while researching {{KEYWORD}} "
        "and thought it was worth reaching out.\n\n"
        "[1-2 sentences connecting {{ORGANIZATION_NAME}} to {{KEYWORD}}]\n\n"
        "[One clear, low-pressure call to action]\n\n"
        "Best regards,\n{{SENDER_NAME}}\n{{SENDER_COMPANY}}"
    ),
    "short_direct": (
        "Hi {{CONTACT_NAME|there}},\n\n"
        "Quick note about {{ORGANIZATION_NAME}} and {{KEYWORD}}.\n\n"
        "[One sentence: the specific opportunity you noticed]\n\n"
        "[One sentence: what you offer, concretely]\n\n"
        "Worth a short chat?\n\n"
        "{{SENDER_NAME}}\n{{SENDER_COMPANY}}"
    ),
    "value_first": (
        "Hi {{CONTACT_NAME|there}},\n\n"
        "Teams working on {{KEYWORD}} often run into [specific problem].\n\n"
        "[One sentence: how you help with that problem]\n\n"
        "Given {{ORGANIZATION_NAME}}'s work in this space, thought it might "
        "be relevant.\n\n"
        "[One clear, low-pressure call to action]\n\n"
        "{{SENDER_NAME}}\n{{SENDER_COMPANY}}"
    ),
}

# Order used for round-robin selection across a campaign's leads.
TEMPLATE_ORDER = ("professional", "short_direct", "value_first")


class TemplateService:
    """Provides base email structures for the email generation agent."""

    def get_template(self, name: str) -> str:
        """Return a template by name; falls back to 'professional'."""
        return EMAIL_TEMPLATES.get(name, EMAIL_TEMPLATES["professional"])

    def pick_for_index(self, index: int) -> str:
        """Round-robin template selection so drafts vary across leads."""
        return TEMPLATE_ORDER[index % len(TEMPLATE_ORDER)]

    def render(self, template: str, variables: Dict[str, str]) -> str:
        """
        Replace ``{{PLACEHOLDER}}`` and ``{{PLACEHOLDER|default}}`` occurrences.

        Variables win over defaults; unknown placeholders without defaults
        (e.g. ``{{SENDER_NAME}}``) are left in place for Phase 3 to fill.
        """
        pattern = re.compile(r"\{\{([A-Z_]+)(?:\|([^}]*))?\}\}")

        def replace(match: "re.Match") -> str:
            key = match.group(1)
            if key in variables:
                return str(variables[key])
            if match.group(2) is not None:
                return match.group(2)
            return match.group(0)  # leave unknown placeholders untouched

        return pattern.sub(replace, template)


template_service = TemplateService()

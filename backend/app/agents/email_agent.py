"""
Email Generation Agent

Drafts a personalized B2B outreach email (subject + body) for a lead using an
AI provider. Sender identity stays as ``{{SENDER_*}}`` placeholders so the
sending phase (Phase 3) can substitute the real user identity, and the draft
is always reviewed by a human before it is ever sent.
"""

import logging
import re
from dataclasses import dataclass

from app.integrations.ai_base import LLMClient, get_ai_client
from app.services.personalization_service import personalization_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a B2B outreach copywriter. Write a short, \
personalized cold email for the lead described below.

Rules:
- 90-150 words in the body, professional and specific, no fluff
- Reference why THIS organization is relevant (connect it to the campaign \
keywords) - never invent facts, awards, customers or claims
- Do not invent the sender's name, company, achievements or pricing; leave \
{{SENDER_NAME}} and {{SENDER_COMPANY}} placeholders where those belong
- Include one clear, low-pressure call to action
- Plain text only (no markdown, no HTML), no subject line inside the body

Respond in EXACTLY this format (no extra text before or after):
SUBJECT: <email subject line, under 70 characters>
BODY: <the email body, may span multiple lines>"""

FOLLOW_UP_SYSTEM_PROMPT = """You are a B2B outreach copywriter writing a \
polite FOLLOW-UP email. The lead received an earlier email but hasn't \
replied yet.

Rules:
- 60-100 words - noticeably shorter than the first email
- Reference the earlier note without guilt-tripping or repeating it verbatim
- Add one new angle, reason, or piece of value
- Never invent facts; leave {{SENDER_NAME}} and {{SENDER_COMPANY}} \
placeholders for the sender identity
- Plain text only, no subject line inside the body
- One clear, low-pressure call to action

Respond in EXACTLY this format (no extra text before or after):
SUBJECT: <email subject line, under 70 characters>
BODY: <the email body, may span multiple lines>"""


@dataclass
class GeneratedEmail:
    """Parsed AI email output for one lead."""

    subject: str
    body: str


class EmailParseError(Exception):
    """The AI response could not be parsed into an email."""


def parse_email(text: str) -> GeneratedEmail:
    """
    Parse the SUBJECT/BODY response format.

    Raises:
        EmailParseError: When subject or body cannot be found.
    """
    if not text or not text.strip():
        raise EmailParseError("empty AI response")

    subject_match = re.search(r"SUBJECT\s*[:\-]\s*(.+)", text, re.IGNORECASE | re.MULTILINE)
    body_match = re.search(
        r"BODY\s*[:\-]\s*(.+?)(?=\n[A-Z][A-Z_ ]+\s*:|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    subject = subject_match.group(1).strip() if subject_match else ""
    body = body_match.group(1).strip() if body_match else ""

    if not subject or not body:
        raise EmailParseError(f"could not parse SUBJECT/BODY from AI response: {text[:200]!r}")

    return GeneratedEmail(subject=subject, body=body)


class EmailGenerationAgent:
    """Generates personalized outreach emails for leads."""

    def __init__(self, client: LLMClient = None) -> None:
        self.client = client or get_ai_client()

    async def generate(self, lead, campaign, template_hint: str = "") -> GeneratedEmail:
        """
        Generate one outreach email for a lead.

        Args:
            lead: Lead ORM instance.
            campaign: Campaign ORM instance.
            template_hint: Optional structure hint from the template service.

        Returns:
            GeneratedEmail with subject and body.
        """
        context = personalization_service.build_context(lead, campaign)
        structure = (
            f"Base the email loosely on this structure:\n{template_hint}\n" if template_hint else ""
        )

        user_prompt = (
            f"Campaign keywords: {', '.join(campaign.keywords or [])}\n"
            f"Campaign description: {campaign.description or 'n/a'}\n"
            "\n"
            f"Organization: {lead.organization_name}\n"
            f"Website: {lead.website}\n"
            f"Contact page: {lead.contact_page_url or 'not found'}\n"
            f"Contact name: {lead.contact_name or 'unknown'}\n"
            f"Job title: {lead.job_title or 'unknown'}\n"
            f"Lead score (0-100): {lead.lead_score}\n"
            "\n"
            f"Personalization context:\n{personalization_service.format_context(context)}\n"
            "\n"
            f"{structure}"
        )

        response = await self.client.complete(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=2048,
            temperature=0.7,  # writing benefits from variety
            model=self.client.default_email_model,
        )

        result = parse_email(response.text)
        logger.info(
            "Generated email for lead %d (%s) subject=%r [%s]",
            lead.id,
            lead.organization_name,
            result.subject,
            response.model,
        )
        return result

    async def generate_follow_up(self, lead, campaign, follow_up_number: int) -> GeneratedEmail:
        """
        Generate a polite follow-up email for a lead that was contacted but
        hasn't replied.
        """
        context = personalization_service.build_context(lead, campaign)

        user_prompt = (
            f"This is follow-up number {follow_up_number} after the original "
            f"outreach email.\n\n"
            f"Campaign keywords: {', '.join(campaign.keywords or [])}\n"
            "\n"
            f"Organization: {lead.organization_name}\n"
            f"Website: {lead.website}\n"
            f"Contact name: {lead.contact_name or 'unknown'}\n"
            f"Lead score (0-100): {lead.lead_score}\n"
            "\n"
            f"Personalization context:\n{personalization_service.format_context(context)}"
        )

        response = await self.client.complete(
            system=FOLLOW_UP_SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=1024,
            temperature=0.7,
            model=self.client.default_email_model,
        )

        result = parse_email(response.text)
        logger.info(
            "Generated follow-up #%d for lead %d (%s) [%s]",
            follow_up_number,
            lead.id,
            lead.organization_name,
            response.model,
        )
        return result

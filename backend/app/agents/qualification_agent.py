"""
Qualification Agent

Scores leads 0-100 with reasoning using an AI provider, based on how well the
organization matches the campaign keywords and how strong the contact
information is. Output format per the development plan:

    SCORE: 87
    REASONING: University research department with multiple clinical research
    programs and publicly listed REDCap-related activities.
    CATEGORY: Educational/Research
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.integrations.ai_base import LLMClient, get_ai_client

logger = logging.getLogger(__name__)

MAX_SCORE = 100

SYSTEM_PROMPT = """You are a B2B lead qualification specialist. Analyze the \
organization described below and score it 0-100 for how promising it is as a \
lead for the given campaign keywords.

Consider:
- Relevance of the organization to the campaign keywords
- Organization type (university, company, nonprofit, government) and its \
likelihood of needing services related to the keywords
- Quality and decision-making potential of the available contact information
- Signals in the website title/description about the organization's focus

Respond in EXACTLY this format (no extra text before or after):
SCORE: <integer 0-100>
REASONING: <2-3 sentences explaining the score>
CATEGORY: <short category label, e.g. Educational/Research, Software/Vendor, \
Media, Healthcare, Consulting>"""


@dataclass
class QualificationResult:
    """Parsed AI qualification output for one lead."""

    score: int
    reasoning: str
    category: str
    signals: List[str] = field(default_factory=list)


class QualificationParseError(Exception):
    """The AI response could not be parsed into a qualification result."""


def parse_qualification(text: str) -> QualificationResult:
    """
    Parse the SCORE/REASONING/CATEGORY response format.

    Tolerant of extra whitespace, lowercase keys and leading prose; raises
    :class:`QualificationParseError` when no score can be found.
    """
    if not text or not text.strip():
        raise QualificationParseError("empty AI response")

    score_match = re.search(r"SCORE\s*[:\-]?\s*(\d{1,3})", text, re.IGNORECASE)
    if not score_match:
        raise QualificationParseError(f"no SCORE found in AI response: {text[:200]!r}")

    score = min(MAX_SCORE, max(0, int(score_match.group(1))))

    reasoning = ""
    reasoning_match = re.search(
        r"REASONING\s*[:\-]?\s*(.+?)(?=\n\s*CATEGORY\s*[:\-]|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if reasoning_match:
        reasoning = " ".join(reasoning_match.group(1).split())

    category = ""
    category_match = re.search(r"CATEGORY\s*[:\-]?\s*(.+)", text, re.IGNORECASE)
    if category_match:
        category = category_match.group(1).strip().splitlines()[0].strip()

    return QualificationResult(score=score, reasoning=reasoning, category=category)


class QualificationAgent:
    """Scores leads using an AI provider."""

    def __init__(self, client: LLMClient = None) -> None:
        self.client = client or get_ai_client()

    async def qualify(self, lead, campaign) -> QualificationResult:
        """
        Qualify one lead against its campaign.

        When intent detection is enabled, the lead's homepage is fetched and
        detected buying signals are included in the prompt and reasoning.

        Args:
            lead: Lead ORM instance (organization, website, contact fields).
            campaign: Campaign ORM instance (keywords, description).

        Returns:
            QualificationResult with a 0-100 score and reasoning.
        """
        from app.core.config import settings

        signals: List[str] = []
        if settings.intent_detection_enabled and lead.website:
            from app.services.intent_service import intent_service

            try:
                signals = await intent_service.detect_signals(
                    lead.website, list(campaign.keywords or [])
                )
            except Exception as exc:  # never let intent detection break scoring
                logger.info("Intent detection skipped for lead %d: %s", lead.id, exc)

        user_prompt = self._build_prompt(lead, campaign, signals)
        response = await self.client.complete(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=512,
            temperature=0.2,  # scoring benefits from low variance
        )

        result = parse_qualification(response.text)
        result.signals = signals
        logger.info(
            "Qualified lead %d (%s): score=%d category=%s signals=%s [%s]",
            lead.id,
            lead.organization_name,
            result.score,
            result.category,
            signals,
            response.model,
        )
        return result

    @staticmethod
    def _build_prompt(lead, campaign, signals: Optional[List[str]] = None) -> str:
        """Assemble the lead/campaign facts for the qualification prompt."""
        lines = [
            f"Campaign keywords: {', '.join(campaign.keywords or [])}",
            f"Campaign description: {campaign.description or 'n/a'}",
            "",
            f"Organization: {lead.organization_name}",
            f"Website: {lead.website}",
            f"Contact page: {lead.contact_page_url or 'not found'}",
            f"Contact name: {lead.contact_name or 'unknown'}",
            f"Job title: {lead.job_title or 'unknown'}",
            f"Email available: {'yes' if lead.email else 'no'}",
            f"Phone available: {'yes' if lead.phone else 'no'}",
        ]
        if signals:
            lines.append(f"Intent signals from their website: {', '.join(signals)}")
        return "\n".join(lines)

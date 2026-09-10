"""
Reply Classification Agent

Classifies an inbound reply into a category using the AI provider, with a
short summary of what the sender said. Falls back to keyword heuristics when
the AI response can't be parsed (the reply is never lost).
"""

import logging
import re
from dataclasses import dataclass

from app.integrations.ai_base import LLMClient, get_ai_client

logger = logging.getLogger(__name__)

# Canonical categories (mirror the Reply model enum)
CATEGORIES = (
    "interested",
    "not_interested",
    "need_more_info",
    "request_meeting",
    "pricing_request",
    "out_of_office",
    "unsubscribe",
    "wrong_contact",
    "other",
)

SYSTEM_PROMPT = """You classify replies to B2B outreach emails. Read the reply \
below and decide the sender's intent.

Choose EXACTLY ONE category from:
- interested: wants to learn more, positive response
- not_interested: explicitly declines
- need_more_info: asks for details/brochure/case study
- request_meeting: proposes a call or meeting
- pricing_request: asks about pricing/costs
- out_of_office: auto-reply or away notice
- unsubscribe: asks to stop receiving emails
- wrong_contact: not the right person, suggests someone else
- other: anything else

Respond in EXACTLY this format (no extra text before or after):
CATEGORY: <category from the list>
SUMMARY: <one sentence describing what the sender said>"""


# Keyword fallback when the AI is unavailable - deliberately conservative
KEYWORD_HINTS = (
    ("unsubscribe", "unsubscribe"),
    ("opt out", "unsubscribe"),
    ("remove me", "unsubscribe"),
    ("not interested", "not_interested"),
    ("out of office", "out_of_office"),
    ("automatic reply", "out_of_office"),
    ("auto-reply", "out_of_office"),
    ("pricing", "pricing_request"),
    ("price", "pricing_request"),
    ("quote", "pricing_request"),
    ("book a meeting", "request_meeting"),
    ("schedule a call", "request_meeting"),
    ("happy to chat", "interested"),
    ("sounds interesting", "interested"),
)


@dataclass
class ReplyClassification:
    """Parsed AI classification for one reply."""

    category: str
    summary: str
    used_ai: bool


def heuristic_classify(text: str) -> ReplyClassification:
    """Keyword-based fallback classification (no AI)."""
    lowered = (text or "").lower()
    for keyword, category in KEYWORD_HINTS:
        if keyword in lowered:
            return ReplyClassification(
                category=category,
                summary="Classified by keyword rules (AI unavailable).",
                used_ai=False,
            )
    return ReplyClassification(
        category="other", summary="Classified by keyword rules (AI unavailable).", used_ai=False
    )


def parse_classification(text: str) -> ReplyClassification:
    """
    Parse the CATEGORY/SUMMARY response format.

    Raises:
        ValueError: If no valid category is found.
    """
    if not text or not text.strip():
        raise ValueError("empty AI response")

    category_match = re.search(r"CATEGORY\s*[:\-]\s*([a-z_]+)", text, re.IGNORECASE)
    if not category_match:
        raise ValueError(f"no CATEGORY found in AI response: {text[:200]!r}")

    category = category_match.group(1).strip().lower()
    if category not in CATEGORIES:
        raise ValueError(f"unknown category {category!r} in AI response")

    summary_match = re.search(r"SUMMARY\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    summary = summary_match.group(1).strip() if summary_match else ""

    return ReplyClassification(category=category, summary=summary, used_ai=True)


class ReplyClassificationAgent:
    """Classifies inbound replies using an AI provider."""

    def __init__(self, client: LLMClient = None) -> None:
        try:
            self.client = client or get_ai_client()
            self.ai_available = True
        except Exception as exc:
            logger.warning("AI provider unavailable for reply classification: %s", exc)
            self.client = None
            self.ai_available = False

    async def classify(self, *, from_email: str, subject: str, body: str) -> ReplyClassification:
        """Classify one reply. Never raises - falls back to heuristics."""
        if not self.ai_available:
            return heuristic_classify(f"{subject}\n{body}")

        user_prompt = f"From: {from_email}\nSubject: {subject or '(no subject)'}\n\n{body[:4000]}"

        try:
            response = await self.client.complete(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                max_tokens=256,
                temperature=0.1,  # classification wants determinism
            )
            return parse_classification(response.text)
        except Exception as exc:
            logger.warning(
                "AI classification failed for reply from %s (%s); using keywords",
                from_email,
                exc,
            )
            return heuristic_classify(f"{subject}\n{body}")

"""
Lead Intent Detection

Phase 5: fetches a lead's homepage and extracts intent signals - hiring
posts, demo/trial CTAs, growth/funding mentions, tech-stack keywords that
overlap the campaign - which sharpen AI qualification scoring.

Failures are silent by design: an unreachable site simply yields no signals.
"""

import asyncio
import logging
import re
from typing import List

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# (signal name, regex over the page text)
SIGNAL_PATTERNS = (
    (
        "hiring",
        re.compile(r"\b(we'?re hiring|we are hiring|join our team|careers|job openings?)\b", re.I),
    ),
    (
        "demo_or_trial_cta",
        re.compile(
            r"\b(book a demo|request a demo|free trial|schedule a demo|get started free)\b", re.I
        ),
    ),
    (
        "growth",
        re.compile(
            r"\b(series [abc] funding|raised \$|recently funded|expanding|scaling our team)\b", re.I
        ),
    ),
    (
        "buying_signals",
        re.compile(r"\b(looking for|seeking a (partner|vendor|agency)|need help with)\b", re.I),
    ),
)

MAX_TEXT_CHARS = 20000
FETCH_TIMEOUT = 10.0


def extract_signals(text: str, campaign_keywords: List[str] = None) -> List[str]:
    """Extract intent signal names from page text (pure function, testable)."""
    signals: List[str] = []
    lowered = (text or "").lower()

    for name, pattern in SIGNAL_PATTERNS:
        if pattern.search(text):
            signals.append(name)

    # Keyword overlap: campaign keywords mentioned on the page
    for keyword in campaign_keywords or []:
        keyword_lower = keyword.strip().lower()
        if len(keyword_lower) >= 4 and keyword_lower in lowered:
            signal = f"mentions:{keyword_lower}"
            if signal not in signals:
                signals.append(signal)

    return signals[:6]


def _page_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)[:MAX_TEXT_CHARS]


class IntentService:
    """Detects buying-intent signals on a lead's website."""

    def __init__(self, timeout: float = FETCH_TIMEOUT) -> None:
        self.timeout = timeout

    async def detect_signals(self, website_url: str, campaign_keywords: List[str]) -> List[str]:
        """
        Fetch the homepage and extract intent signals.

        Never raises - an unreachable or non-HTML site returns no signals.
        """
        url = website_url.strip()
        if url and not url.lower().startswith(("http://", "https://")):
            url = f"https://{url}"

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; LeadGenBot/1.0)"},
            ) as client:
                response = await client.get(url)
            if response.status_code != 200:
                return []
            return extract_signals(_page_text(response.text), campaign_keywords)
        except Exception as exc:
            logger.info("Intent detection failed for %s: %s", url, exc)
            return []


intent_service = IntentService()

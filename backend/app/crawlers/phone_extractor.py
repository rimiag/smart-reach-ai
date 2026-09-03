"""
Phone Extractor

Extracts phone numbers from crawled HTML pages.

Strategy (best signals first):

1. ``tel:`` links - the site published these deliberately as callable numbers
2. Regex patterns over the visible text (email matches are removed first so
   number-like fragments inside addresses are not picked up)

Matches are sanity-checked (7-15 digits, not all-identical digits) to filter
out dates, order numbers and placeholder strings like 000-000-0000.
"""

import logging
import re
from typing import Iterable, List

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TEL_HREF_REGEX = re.compile(r"href=[\"']tel:([^\"']+)[\"']", re.IGNORECASE)

PHONE_PATTERNS = (
    # International with leading +: +44 20 7946 0958, +1-555-123-4567
    re.compile(r"\+\d{1,3}(?:[\s.\-]?\(?\d{1,5}\)?)(?:[\s.\-]?\d{2,4}){1,4}"),
    # US style with parentheses: (555) 123-4567
    re.compile(r"\(\d{3}\)\s?\d{3}(?:[\s.\-]?\d{4})"),
    # Grouped with separators: 555-123-4567 / 555.123.4567
    re.compile(r"\b\d{3}[\s.\-]\d{3}[\s.\-]\d{4}\b"),
)


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def _is_plausible(match: str) -> bool:
    digits = _digits(match)
    if not 7 <= len(digits) <= 15:
        return False
    if len(set(digits)) == 1:  # e.g. 000-000-0000 placeholders
        return False
    return True


def _clean(match: str) -> str:
    return re.sub(r"\s+", " ", match).strip()


class PhoneExtractor:
    """Extracts unique, plausible phone numbers from HTML pages."""

    def extract(self, html: str, exclude_texts: Iterable[str] = ()) -> List[str]:
        """
        Return unique phone numbers found in ``html`` (best first).

        Args:
            html: The raw page HTML.
            exclude_texts: Strings (e.g. extracted emails) removed from the
                text before pattern matching.
        """
        if not html:
            return []

        found: List[str] = []
        seen_digits: set = set()

        # 1. tel: links
        for match in TEL_HREF_REGEX.findall(html):
            value = _clean(match)
            key = _digits(value)
            if key and key in seen_digits:
                continue
            if _is_plausible(value):
                seen_digits.add(key)
                found.append(value)

        # 2. Visible text with emails (and other exclusions) removed first
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        for excluded in exclude_texts:
            text = text.replace(excluded, "")

        for pattern in PHONE_PATTERNS:
            for match in pattern.findall(text):
                if not _is_plausible(match):
                    continue
                cleaned = _clean(match)
                key = _digits(cleaned)
                if key in seen_digits:
                    continue
                seen_digits.add(key)
                found.append(cleaned)

        return found

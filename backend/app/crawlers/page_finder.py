"""
Contact Page Finder

Finds the pages on a website most likely to contain contact information
(contact, about, team, impressum, ...) by scoring same-domain links on the
homepage.
"""

import logging
from typing import Dict, List
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# High-value link texts / paths - almost always contain contact details.
PRIMARY_HINTS = ("contact", "kontakt", "impressum", "contacto", "get in touch", "reach us")
# Secondary - may contain contacts (team/staff pages).
SECONDARY_HINTS = ("about", "team", "staff", "people", "who we are")

SKIP_PREFIXES = ("mailto:", "tel:", "javascript:", "#", "data:")

# Direct document/media links are not worth crawling for contacts.
SKIP_EXTENSIONS = (
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
    ".rar",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".mp4",
    ".mp3",
)


class ContactPageFinder:
    """Scores same-domain homepage links to find likely contact pages."""

    def find(self, html: str, base_url: str, max_pages: int = 4) -> List[str]:
        """
        Return up to ``max_pages`` absolute URLs, best candidates first.

        Args:
            html: Homepage HTML.
            base_url: The homepage URL (used to resolve relative links and
                determine the site's domain).
            max_pages: Maximum number of candidate URLs to return.
        """
        if not html:
            return []

        base_domain = urlparse(base_url).netloc.lower()
        scored: Dict[str, int] = {}

        soup = BeautifulSoup(html, "html.parser")
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            if not href or href.lower().startswith(SKIP_PREFIXES):
                continue

            absolute = urljoin(base_url, href)
            parsed = urlparse(absolute)
            if parsed.scheme not in ("http", "https"):
                continue
            if parsed.netloc.lower() != base_domain:
                continue  # stay on the same site
            if parsed.path.lower().endswith(SKIP_EXTENSIONS):
                continue

            link_text = anchor.get_text(" ", strip=True).lower()
            path = parsed.path.lower()

            score = 0
            if any(hint in link_text for hint in PRIMARY_HINTS):
                score += 3
            if any(hint in path for hint in PRIMARY_HINTS):
                score += 2
            if any(hint in link_text for hint in SECONDARY_HINTS):
                score += 1
            if any(hint in path for hint in SECONDARY_HINTS):
                score += 1
            if score <= 0:
                continue

            candidate = absolute.split("#", 1)[0]
            scored[candidate] = max(scored.get(candidate, 0), score)

        ranked = sorted(scored.items(), key=lambda item: item[1], reverse=True)
        return [url for url, _ in ranked[:max_pages]]

"""
Email Extractor

Extracts email addresses from crawled HTML pages.

Strategy (best signals first):

1. ``mailto:`` links - the site published these deliberately as contacts
2. Plain-text regex over the visible page text (scripts/styles stripped)

Junk filtering removes asset-like matches (``logo@2x.png``), placeholder
domains (example.com, ...) and no-reply style addresses.
"""

import logging
import re
from typing import List

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
MAILTO_REGEX = re.compile(r"mailto:\s*([^\"'>?\s]+)", re.IGNORECASE)

# File endings that produce fake matches such as "logo@2x.png" or "app@app.js".
MEDIA_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".css", ".js")

# Placeholder / irrelevant domains common on template and SaaS sites.
JUNK_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "domain.com",
    "yourdomain.com",
    "yourdomain.de",
    "email.com",
    "test.com",
    "test.de",
    "site.com",
    "website.com",
    "mail.com",
    "sentry.io",
    "wixpress.com",
    "godaddy.com",
}

# Local parts that are never useful for outreach.
JUNK_LOCAL_PARTS = ("noreply", "no-reply", "donotreply", "do-not-reply", "postmaster")


def is_likely_junk(email: str) -> bool:
    """Return True when an email match is a placeholder/asset, not a contact."""
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return True
    local, _, domain = email.partition("@")
    if domain.endswith(MEDIA_EXTENSIONS):
        return True
    if domain in JUNK_DOMAINS or domain.startswith(("sentry", "wixpress")):
        return True
    return any(local == j or local.startswith(j) for j in JUNK_LOCAL_PARTS)


class EmailExtractor:
    """Extracts unique, plausible contact emails from HTML pages."""

    MAX_EMAIL_LENGTH = 254  # RFC 5321 maximum

    def extract(self, html: str) -> List[str]:
        """Return unique lowercase emails found in ``html`` (best first)."""
        if not html:
            return []

        found: List[str] = []

        # 1. mailto: links
        for match in MAILTO_REGEX.findall(html):
            candidate = match.strip().strip(".").lower()
            if EMAIL_REGEX.fullmatch(candidate) and not is_likely_junk(candidate):
                found.append(candidate)

        # 2. Visible text (scripts/styles removed to skip JS and asset noise)
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)

        for match in EMAIL_REGEX.findall(text):
            candidate = match.strip().strip(".").lower()
            if len(candidate) <= self.MAX_EMAIL_LENGTH and not is_likely_junk(candidate):
                found.append(candidate)

        # Deduplicate, preserving order (mailto links stay first).
        return list(dict.fromkeys(found))

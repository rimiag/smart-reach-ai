"""
Crawler Agent

Visits websites discovered by the search agent, respects robots.txt and rate
limits, locates contact pages and extracts publicly available contact details.

Used by the crawl tasks (Iteration 1.5). One agent instance shares a single
HTTP client and a politeness rate limiter across all concurrent lookups, and
must be used as an async context manager (or closed explicitly).
"""

import asyncio
import logging
import time
from typing import List, Optional, Tuple
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.crawlers.email_extractor import EmailExtractor
from app.crawlers.page_finder import ContactPageFinder
from app.crawlers.phone_extractor import PhoneExtractor
from app.crawlers.robots_txt import RobotsTxtHandler
from app.schemas.contact_info import ContactInfo

logger = logging.getLogger(__name__)

# Contact page candidates examined per website (on top of the homepage).
MAX_CONTACT_PAGES = 4


class _RateLimiter:
    """Enforces a minimum interval between requests (shared per agent)."""

    def __init__(self, min_interval_seconds: float) -> None:
        self.min_interval = max(0.0, float(min_interval_seconds))
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        if self.min_interval <= 0:
            return
        async with self._lock:
            delay = self._last_request + self.min_interval - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_request = time.monotonic()


class CrawlerAgent:
    """Polite crawler: robots.txt checks, contact-page finding, extraction."""

    def __init__(self) -> None:
        self.rate_limiter = _RateLimiter(settings.crawler_request_delay)
        self.robots_handler = RobotsTxtHandler()
        self.page_finder = ContactPageFinder()
        self.email_extractor = EmailExtractor()
        self.phone_extractor = PhoneExtractor()
        self._client = httpx.AsyncClient(
            timeout=settings.crawler_timeout,
            headers={"User-Agent": settings.crawler_user_agent},
            follow_redirects=True,
        )

    async def __aenter__(self) -> "CrawlerAgent":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Public pipeline
    # ------------------------------------------------------------------
    async def can_crawl(self, url: str) -> bool:
        """Check robots.txt permission for the URL with our user agent."""
        return await self.robots_handler.can_fetch(url, settings.crawler_user_agent)

    async def find_contact_pages(
        self, base_url: str, homepage_html: Optional[str] = None
    ) -> List[str]:
        """Locate likely contact pages; falls back to guessing ``/contact``."""
        html = homepage_html
        if html is None:
            html = await self._get(base_url)

        candidates = self.page_finder.find(html or "", base_url, max_pages=MAX_CONTACT_PAGES)
        if not candidates:
            candidates = [urljoin(base_url, "/contact")]
        return candidates

    async def extract_contact_info(self, url: str) -> Tuple[List[str], List[str], Optional[str]]:
        """
        Fetch a single page and extract from it.

        Returns:
            (emails, phones, organization_name)
        """
        html = await self._get(url)
        if html is None:
            return [], [], None
        emails = self.email_extractor.extract(html)
        phones = self.phone_extractor.extract(html, exclude_texts=emails)
        return emails, phones, self._extract_org(html)

    async def process_website(self, url: str) -> Tuple[str, Optional[ContactInfo], Optional[str]]:
        """
        Full pipeline for one website: robots check -> homepage -> contact
        pages -> extraction.

        Returns:
            ``(status, contact_info, error)`` where status is ``"crawled"``
            (page(s) fetched; ``contact_info`` may still lack contacts),
            ``"skipped"`` (robots.txt) or ``"failed"`` (unreachable).
        """
        if not await self.can_crawl(url):
            return "skipped", None, "blocked by robots.txt"

        homepage = await self._get(url)
        if homepage is None:
            return "failed", None, "homepage could not be fetched"

        contact = ContactInfo(website=url, source_urls=[url])

        organization = self._extract_org(homepage)
        if organization:
            contact.organization_name = organization

        emails = self.email_extractor.extract(homepage)
        phones = self.phone_extractor.extract(homepage, exclude_texts=emails)
        best_page = url if (emails or phones) else None
        best_score = len(emails) + len(phones)

        for page_url in await self.find_contact_pages(url, homepage_html=homepage):
            if page_url == url:
                continue
            page_html = await self._get(page_url)
            if page_html is None:
                continue
            contact.source_urls.append(page_url)

            page_emails = self.email_extractor.extract(page_html)
            page_phones = self.phone_extractor.extract(page_html, exclude_texts=page_emails)
            emails.extend(page_emails)
            phones.extend(page_phones)

            score = len(page_emails) + len(page_phones)
            if score > best_score:
                best_score = score
                best_page = page_url

        contact.emails = list(dict.fromkeys(email.lower() for email in emails))
        contact.phones = list(dict.fromkeys(phones))
        if best_page and (contact.emails or contact.phones):
            contact.contact_page_url = best_page

        if not contact.emails and not contact.phones:
            return "crawled", contact, "no contact information found"

        return "crawled", contact, None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    async def _get(self, url: str) -> Optional[str]:
        """Fetch a URL politely; return HTML text or None on any failure."""
        await self.rate_limiter.wait()
        try:
            response = await self._client.get(url)
        except httpx.HTTPError as exc:
            logger.info("Fetch failed for %s: %s", url, exc)
            return None

        if response.status_code != 200:
            logger.info("Fetch of %s returned HTTP %d", url, response.status_code)
            return None

        content_type = response.headers.get("content-type", "")
        if content_type and not any(
            marker in content_type for marker in ("text/html", "text/plain", "application/xhtml")
        ):
            logger.info("Skipping non-HTML content at %s (%s)", url, content_type)
            return None

        return response.text

    @staticmethod
    def _extract_org(html: str) -> Optional[str]:
        """Best-effort organization name from og:site_name or <title>."""
        try:
            soup = BeautifulSoup(html, "html.parser")

            og_site_name = soup.find("meta", property="og:site_name")
            if og_site_name and (og_site_name.get("content") or "").strip():
                return og_site_name["content"].strip()[:200]

            title_tag = soup.find("title")
            if title_tag:
                raw = title_tag.get_text(strip=True)
                for separator in ("|", "–", "—", "::", "-"):
                    if separator in raw:
                        raw = raw.split(separator)[0]
                        break
                return raw.strip()[:200] or None
        except Exception:  # never let title parsing break a crawl
            return None
        return None

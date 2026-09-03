"""
Search Provider Base

Shared models and the abstract interface every search provider implements.
Providers only translate a keyword into a list of SearchResult objects; all
filtering and deduplication happens in the search agent.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def extract_domain(url: str) -> str:
    """
    Extract the lowercase hostname (without a leading 'www.' and port) from a URL.

    Returns an empty string when the URL cannot be parsed.
    """
    try:
        host = urlparse(url).netloc.lower()
    except Exception:  # malformed URLs should never break a search run
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host.split(":")[0]


@dataclass
class SearchResult:
    """A single organic result returned by a search provider."""

    url: str
    title: str = ""
    snippet: str = ""
    domain: str = ""
    position: int = 0

    def __post_init__(self) -> None:
        if not self.domain:
            self.domain = extract_domain(self.url)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage in ResearchResult.extra_data."""
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "domain": self.domain,
            "position": self.position,
        }


class SearchProviderError(Exception):
    """Raised when a search provider is unavailable, unconfigured or failing."""


class SearchProvider(ABC):
    """
    Abstract base class for search provider integrations.

    Concrete providers set ``name`` and implement :meth:`search`. They should
    raise :class:`SearchProviderError` on configuration problems or repeated
    request failures so callers can fall back or abort cleanly.
    """

    name: str = "base"

    @property
    def is_configured(self) -> bool:
        """Whether this provider has the credentials it needs."""
        return True

    @abstractmethod
    async def search(self, keyword: str, limit: int) -> List[SearchResult]:
        """
        Search the web for ``keyword`` and return up to ``limit`` results.

        Raises:
            SearchProviderError: On misconfiguration or after exhausting retries.
        """

    # ------------------------------------------------------------------
    # Shared HTTP helper
    # ------------------------------------------------------------------
    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Perform an HTTP request and parse the JSON body, with retries.

        Raises:
            SearchProviderError: On non-2xx responses or unparseable bodies
                after ``settings.search_max_retries`` attempts.
        """
        last_error: Optional[str] = None

        for attempt in range(settings.search_max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=settings.search_timeout) as client:
                    response = await client.request(method, url, params=params, headers=headers)

                if response.status_code == 429:
                    last_error = f"{self.name}: rate limited (HTTP 429)"
                    logger.warning("%s - attempt %d", last_error, attempt + 1)
                    continue

                if response.status_code >= 400:
                    # Client errors (bad key, bad params) will not improve with
                    # a retry for 4xx codes other than 429 - fail immediately.
                    raise SearchProviderError(
                        f"{self.name}: HTTP {response.status_code} - {response.text[:300]}"
                    )

                try:
                    return response.json()
                except ValueError as exc:
                    raise SearchProviderError(
                        f"{self.name}: invalid JSON response - {exc}"
                    ) from exc

            except httpx.HTTPError as exc:
                last_error = f"{self.name}: request failed - {exc}"
                logger.warning("%s - attempt %d", last_error, attempt + 1)

        raise SearchProviderError(last_error or f"{self.name}: request failed")

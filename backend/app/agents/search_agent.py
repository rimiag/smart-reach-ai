"""
Search Agent

Discovers websites for campaign keywords using a configured search provider
(Bing, Google Custom Search or SerpAPI), filters out low-quality results and
deduplicates domains across keywords.
"""

import logging
from typing import List, Optional

from app.core.config import settings
from app.integrations.bing_search import BingSearchProvider
from app.integrations.google_search import GoogleSearchProvider
from app.integrations.search_base import (
    SearchProvider,
    SearchProviderError,
    SearchResult,
    extract_domain,
)
from app.integrations.serpapi_search import SerpAPISearchProvider

logger = logging.getLogger(__name__)

# Domains that are never useful as B2B leads (social networks and the search
# engines themselves). Merged with settings.search_blocked_domains.
DEFAULT_BLOCKED_DOMAINS = {
    "facebook.com",
    "m.facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
    "pinterest.com",
    "snapchat.com",
    "reddit.com",
    "google.com",
    "bing.com",
    "duckduckgo.com",
    "yahoo.com",
    "baidu.com",
}

# Non-HTML resources a crawler cannot extract contacts from.
BLOCKED_EXTENSIONS = (
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".rar",
    ".7z",
    ".gz",
    ".csv",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".exe",
    ".dmg",
    ".apk",
    ".iso",
)


def get_search_provider(preferred: Optional[str] = None) -> SearchProvider:
    """
    Return a configured search provider.

    Args:
        preferred: Provider name (bing, google, serpapi) or None/"auto" to pick
            the first provider with credentials in this order: serpapi, google,
            bing (SerpAPI first because the hosted Bing v7 API was retired).

    Raises:
        SearchProviderError: If no provider is configured.
    """
    providers = {
        "bing": BingSearchProvider,
        "google": GoogleSearchProvider,
        "serpapi": SerpAPISearchProvider,
    }

    choice = (preferred or settings.search_provider or "auto").lower()

    if choice != "auto":
        provider_cls = providers.get(choice)
        if provider_cls is None:
            raise SearchProviderError(f"Unknown search provider: {choice}")
        provider = provider_cls()
        if not provider.is_configured:
            raise SearchProviderError(
                f"Search provider '{choice}' is selected but not configured "
                f"(missing API credentials)"
            )
        return provider

    # Auto mode: prefer a provider that is actually usable.
    for name in ("serpapi", "google", "bing"):
        provider = providers[name]()
        if provider.is_configured:
            logger.info("Using search provider: %s", name)
            return provider

    raise SearchProviderError(
        "No search provider configured. Set at least one of SERPAPI_KEY, "
        "GOOGLE_SEARCH_API_KEY (+ GOOGLE_SEARCH_ENGINE_ID) or "
        "BING_SEARCH_API_KEY."
    )


class SearchAgent:
    """
    Agent for discovering websites relevant to campaign keywords.

    Wraps a search provider and adds validation (drop social networks,
    non-HTML documents, malformed URLs) plus domain-level deduplication.
    """

    def __init__(self, provider: Optional[SearchProvider] = None) -> None:
        self.provider = provider or get_search_provider()

    async def search(self, keyword: str, limit: Optional[int] = None) -> List[SearchResult]:
        """
        Search for websites relevant to the keyword.

        Args:
            keyword: The search term.
            limit: Maximum results; defaults to settings.search_results_per_keyword.

        Returns:
            Validated search results, deduplicated by domain, ordered by position.

        Raises:
            SearchProviderError: If the provider fails for this keyword.
        """
        limit = limit or settings.search_results_per_keyword

        raw_results = await self.provider.search(keyword, limit)
        logger.info(
            "Keyword %r: %d raw results from %s",
            keyword,
            len(raw_results),
            self.provider.name,
        )

        validated = [r for r in raw_results if self.validate_result(r)]
        deduplicated = self.deduplicate_results(validated)

        dropped = len(raw_results) - len(deduplicated)
        if dropped:
            logger.info("Keyword %r: dropped %d invalid/duplicate results", keyword, dropped)

        return deduplicated

    def validate_result(self, result: SearchResult) -> bool:
        """
        Filter out irrelevant or low-quality results.

        Rejects: empty/undecodable URLs, non-HTTP(S) schemes, blocked domains
        (social networks, search engines), IP-literal hosts and non-HTML
        documents (PDF, Office files, archives, media, ...).
        """
        if not result.url or not result.domain:
            return False

        lowered_url = result.url.lower().strip()

        if not lowered_url.startswith(("http://", "https://")):
            return False

        # Document/media URLs - the crawler cannot extract contacts from them.
        path = lowered_url.split("?", 1)[0].split("#", 1)[0]
        if path.endswith(BLOCKED_EXTENSIONS):
            return False

        if self.is_blocked_domain(result.domain):
            return False

        return True

    def is_blocked_domain(self, domain: str) -> bool:
        """Check a domain against the built-in and configured block lists."""
        domain = domain.lower().strip()

        # Match the registrable domain: sub.domain.facebook.com -> facebook.com
        parts = domain.split(".")
        registrable = ".".join(parts[-2:]) if len(parts) >= 2 else domain

        if domain in DEFAULT_BLOCKED_DOMAINS or registrable in DEFAULT_BLOCKED_DOMAINS:
            return True

        if domain in self._extra_blocked_domains():
            return True

        return False

    def _extra_blocked_domains(self) -> set:
        """Extra blocked domains from settings (comma-separated)."""
        raw = (settings.search_blocked_domains or "").strip()
        if not raw:
            return set()
        return {d.strip().lower() for d in raw.split(",") if d.strip()}

    def deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Remove duplicate domains, keeping the highest-ranked result per domain.
        """
        seen_domains: set = set()
        unique: List[SearchResult] = []

        for result in sorted(results, key=lambda r: r.position or 0):
            domain = extract_domain(result.url) or result.domain
            if not domain or domain in seen_domains:
                continue
            seen_domains.add(domain)
            result.domain = domain
            unique.append(result)

        return unique

"""
SerpAPI Integration

Implements the SerpAPI Google search API (https://serpapi.com/search).

Requires ``SERPAPI_KEY``. SerpAPI returns up to 100 organic results per
request; pagination is available via the ``start`` parameter if ever needed.
"""

import logging
from typing import Any, Dict, List

from app.core.config import settings
from app.integrations.search_base import SearchProvider, SearchProviderError, SearchResult

logger = logging.getLogger(__name__)


class SerpAPISearchProvider(SearchProvider):
    """Search provider backed by SerpAPI (Google results)."""

    name = "serpapi"

    ENDPOINT = "https://serpapi.com/search"

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key or settings.serpapi_key

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def search(self, keyword: str, limit: int) -> List[SearchResult]:
        """
        Search SerpAPI for ``keyword``.
        """
        if not self.is_configured:
            raise SearchProviderError("serpapi: SERPAPI_KEY is not configured")

        params: Dict[str, Any] = {
            "engine": "google",
            "q": keyword,
            "api_key": self.api_key,
            "num": max(10, min(limit, 100)),
        }

        data = await self._request_json("GET", self.ENDPOINT, params=params)

        if data.get("error"):
            # SerpAPI reports quota/auth problems inside a 200 response body.
            raise SearchProviderError(f"serpapi: {data['error']}")

        organic = data.get("organic_results") or []
        results: List[SearchResult] = []
        for idx, item in enumerate(organic[:limit]):
            results.append(
                SearchResult(
                    url=item.get("link", "") or "",
                    title=item.get("title", "") or "",
                    snippet=item.get("snippet", "") or "",
                    position=idx + 1,
                )
            )

        logger.info("SerpAPI search for %r returned %d results", keyword, len(results))
        return results

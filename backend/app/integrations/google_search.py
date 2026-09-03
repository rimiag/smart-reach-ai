"""
Google Custom Search Integration

Implements the Google Custom Search JSON API (Programmable Search Engine).

Requires ``GOOGLE_SEARCH_API_KEY`` and ``GOOGLE_SEARCH_ENGINE_ID``. The
API returns at most 10 results per request and serves at most 100 results
per keyword, so ``search`` paginates with the ``start`` parameter until the
requested limit is reached.
"""

import asyncio
import logging
from typing import Any, Dict, List

from app.core.config import settings
from app.integrations.search_base import SearchProvider, SearchProviderError, SearchResult

logger = logging.getLogger(__name__)


class GoogleSearchProvider(SearchProvider):
    """Search provider backed by the Google Custom Search JSON API."""

    name = "google"

    ENDPOINT = "https://www.googleapis.com/customsearch/v1"

    # API limits
    MAX_PER_REQUEST = 10
    MAX_START_INDEX = 91  # start + count must stay <= 100

    def __init__(self, api_key: str = "", engine_id: str = "") -> None:
        self.api_key = api_key or settings.google_search_api_key
        self.engine_id = engine_id or settings.google_search_engine_id

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.engine_id)

    async def search(self, keyword: str, limit: int) -> List[SearchResult]:
        """
        Search Google for ``keyword``, paginating 10 results at a time.
        """
        if not self.is_configured:
            raise SearchProviderError(
                "google: GOOGLE_SEARCH_API_KEY / GOOGLE_SEARCH_ENGINE_ID not configured"
            )

        results: List[SearchResult] = []
        start = 1

        while len(results) < limit and start <= self.MAX_START_INDEX:
            params: Dict[str, Any] = {
                "key": self.api_key,
                "cx": self.engine_id,
                "q": keyword,
                "num": min(self.MAX_PER_REQUEST, limit - len(results)),
                "start": start,
            }

            data = await self._request_json("GET", self.ENDPOINT, params=params)
            items = data.get("items") or []

            if not items:
                break  # no further pages for this keyword

            for item in items:
                results.append(
                    SearchResult(
                        url=item.get("link", ""),
                        title=item.get("title", "") or "",
                        snippet=item.get("snippet", "") or "",
                        position=len(results) + 1,
                    )
                )

            start += self.MAX_PER_REQUEST
            # Be polite to the API between pages of the same keyword.
            await asyncio.sleep(0.2)

        logger.info("Google search for %r returned %d results", keyword, len(results))
        return results[:limit]

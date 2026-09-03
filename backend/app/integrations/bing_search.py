"""
Bing Search Integration

Implements the Bing Web Search v7 REST API
(``settings.bing_search_endpoint``).

Note: Microsoft retired the hosted Bing Search v7 API in August 2025. The
endpoint is configurable so this provider also works against any
v7-compatible replacement endpoint (e.g. Azure "Grounding with Bing" proxies
or self-hosted equivalents). Configure ``BING_SEARCH_API_KEY`` and, if needed,
``BING_SEARCH_ENDPOINT``.
"""

import logging
from typing import Any, Dict, List

from app.core.config import settings
from app.integrations.search_base import SearchProvider, SearchProviderError, SearchResult

logger = logging.getLogger(__name__)


class BingSearchProvider(SearchProvider):
    """Search provider backed by the Bing Web Search v7 API."""

    name = "bing"

    def __init__(self, api_key: str = "", endpoint: str = "") -> None:
        self.api_key = api_key or settings.bing_search_api_key
        self.endpoint = endpoint or settings.bing_search_endpoint

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def search(self, keyword: str, limit: int) -> List[SearchResult]:
        """
        Search Bing for ``keyword``.

        Bing returns up to 50 web results per request, which covers the
        per-keyword limits used by campaigns.
        """
        if not self.is_configured:
            raise SearchProviderError("bing: BING_SEARCH_API_KEY is not configured")

        count = max(1, min(limit, 50))
        params: Dict[str, Any] = {
            "q": keyword,
            "count": count,
            "offset": 0,
            "responseFilter": "Webpages",
            "textFormat": "Raw",
            "safeSearch": "Off",
        }
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}

        data = await self._request_json("GET", self.endpoint, params=params, headers=headers)

        web_pages = (data.get("webPages") or {}).get("value") or []
        results: List[SearchResult] = []
        for idx, page in enumerate(web_pages[:limit]):
            results.append(
                SearchResult(
                    url=page.get("url", ""),
                    title=page.get("name", "") or "",
                    snippet=page.get("snippet", "") or "",
                    position=idx + 1,
                )
            )

        logger.info("Bing search for %r returned %d results", keyword, len(results))
        return results

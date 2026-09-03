"""
Robots.txt Handler

Fetches and caches robots.txt files so the crawler respects each site's
crawling rules. Behaviour follows RFC 9309 where practical:

* 2xx              -> parse and honour the rules
* 401 / 403        -> complete disallow (the site forbids robots)
* other 4xx (404)  -> no rules published: crawling allowed
* 429 / 5xx        -> temporarily unavailable: disallow for this run
* network error    -> disallow for this run (conservative), not cached
"""

import logging
import time
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)


class RobotsTxtHandler:
    """Robots.txt lookup with an in-memory per-domain cache."""

    CACHE_TTL_SECONDS = 3600  # successful parses are cached for an hour
    UNAVAILABLE_TTL_SECONDS = 60  # 429/5xx outcomes cached briefly
    FETCH_TIMEOUT_SECONDS = 10

    def __init__(self) -> None:
        # domain -> (cached_at, parser_or_None, fallback_decision)
        self._cache: Dict[str, Tuple[float, Optional[RobotFileParser], bool]] = {}

    async def can_fetch(self, url: str, user_agent: str) -> bool:
        """Check whether ``user_agent`` may crawl ``url`` per robots.txt."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False

        domain = parsed.netloc.lower()
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        entry = self._cache.get(domain)
        if entry is not None:
            cached_at, parser, fallback = entry
            ttl = self.CACHE_TTL_SECONDS if parser is not None else self.UNAVAILABLE_TTL_SECONDS
            if time.monotonic() - cached_at < ttl:
                return self._decide(parser, fallback, url, user_agent)

        parser, fallback = await self._fetch_rules(robots_url, user_agent)
        self._cache[domain] = (time.monotonic(), parser, fallback)
        return self._decide(parser, fallback, url, user_agent)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    async def _fetch_rules(
        self, robots_url: str, user_agent: str
    ) -> Tuple[Optional[RobotFileParser], bool]:
        """
        Fetch robots.txt and return ``(parser, fallback)``.

        ``parser`` is None when no rules could be retrieved; ``fallback`` is
        the decision to use in that situation.
        """
        try:
            async with httpx.AsyncClient(
                timeout=self.FETCH_TIMEOUT_SECONDS, follow_redirects=True
            ) as client:
                response = await client.get(robots_url, headers={"User-Agent": user_agent})
        except httpx.HTTPError as exc:
            logger.warning("robots.txt fetch failed for %s: %s", robots_url, exc)
            return None, False  # conservative: skip this domain for this run

        status = response.status_code

        if status == 200:
            parser = RobotFileParser()
            parser.parse(response.text.splitlines())
            return parser, True

        if status in (401, 403):
            logger.info("robots.txt %d for %s - disallowing domain", status, robots_url)
            return None, False

        if 400 <= status < 500:
            # No robots.txt (or another client error): crawling allowed.
            return None, True

        # 429 / 5xx - unavailable: disallow for now, cached briefly.
        logger.warning("robots.txt %d for %s - treating as unavailable", status, robots_url)
        return None, False

    @staticmethod
    def _decide(
        parser: Optional[RobotFileParser],
        fallback: bool,
        url: str,
        user_agent: str,
    ) -> bool:
        if parser is None:
            return fallback
        try:
            return parser.can_fetch(user_agent, url)
        except Exception:
            # Malformed robots.txt should not crash a crawl - allow.
            return True

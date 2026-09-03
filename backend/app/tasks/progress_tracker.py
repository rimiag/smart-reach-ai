"""
Progress Tracker

Tracks campaign research progress in Redis so the API can report live status
while Celery workers run the search/crawl pipeline.

Entries are JSON documents stored under ``research_progress:{campaign_id}``
with a 7 day TTL. The shape mirrors the ``ResearchProgress`` schema plus a few
internal fields:

{
    "campaign_id": 1,
    "status": "researching",
    "current_step": "Searching: crm software",
    "progress_percentage": 40.0,
    "websites_found": 12,
    "websites_crawled": 0,
    "contacts_found": 0,
    "leads_created": 0,
    "keywords_total": 5,
    "keywords_completed": 2,
    "started_at": "2026-08-31T10:00:00",
    "updated_at": "2026-08-31T10:01:23",
    "error": null
}

All methods degrade gracefully: if Redis is unreachable the tracker logs a
warning and returns None / does nothing, so research still works (only live
progress reporting is lost) and the API falls back to database-derived stats.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import redis
import redis.asyncio as redis_asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)

PROGRESS_KEY_PREFIX = "research_progress"
PROGRESS_TTL_SECONDS = 7 * 24 * 3600  # keep entries for a week


class ProgressTracker:
    """Redis-backed progress tracking for campaign research runs."""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self.redis_url = redis_url or settings.redis_url

    # ------------------------------------------------------------------
    # Keys
    # ------------------------------------------------------------------
    @staticmethod
    def _key(campaign_id: int) -> str:
        return f"{PROGRESS_KEY_PREFIX}:{campaign_id}"

    # ------------------------------------------------------------------
    # Sync API (Celery tasks)
    # ------------------------------------------------------------------
    def _sync_client(self) -> redis.Redis:
        return redis.Redis.from_url(self.redis_url, decode_responses=True)

    def initialize(
        self,
        campaign_id: int,
        keywords_total: int = 0,
        current_step: str = "Queued",
    ) -> None:
        """Create a fresh progress entry for a campaign research run."""
        now = datetime.utcnow().isoformat()
        entry: Dict[str, Any] = {
            "campaign_id": campaign_id,
            "status": "researching",
            "current_step": current_step,
            "progress_percentage": 0.0,
            "websites_found": 0,
            "websites_crawled": 0,
            "contacts_found": 0,
            "leads_created": 0,
            "keywords_total": keywords_total,
            "keywords_completed": 0,
            "started_at": now,
            "updated_at": now,
            "error": None,
        }
        self._write(campaign_id, entry)

    def update(self, campaign_id: int, **fields: Any) -> None:
        """Merge fields into the progress entry (reads then writes)."""
        current = self.get_progress(campaign_id) or {
            "campaign_id": campaign_id,
            "status": "researching",
        }
        current.update(fields)
        current["updated_at"] = datetime.utcnow().isoformat()
        self._write(campaign_id, current)

    def increment(self, campaign_id: int, field: str, amount: int = 1) -> None:
        """Increment a numeric counter in the progress entry."""
        current = self.get_progress(campaign_id)
        if current is None:
            return
        current[field] = int(current.get(field, 0)) + amount
        current["updated_at"] = datetime.utcnow().isoformat()
        self._write(campaign_id, current)

    def set_step(
        self,
        campaign_id: int,
        current_step: str,
        progress_percentage: Optional[float] = None,
    ) -> None:
        """Update the current step (and optionally the percentage)."""
        fields: Dict[str, Any] = {"current_step": current_step}
        if progress_percentage is not None:
            fields["progress_percentage"] = round(float(progress_percentage), 1)
        self.update(campaign_id, **fields)

    def finish(self, campaign_id: int) -> None:
        """Mark the research run as finished successfully."""
        self.update(
            campaign_id,
            status="ready",
            current_step="Research complete",
            progress_percentage=100.0,
            error=None,
        )

    def fail(self, campaign_id: int, error: str) -> None:
        """Mark the research run as failed with an error message."""
        self.update(
            campaign_id,
            status="failed",
            current_step="Research failed",
            error=error,
        )

    def get_progress(self, campaign_id: int) -> Optional[Dict[str, Any]]:
        """Return the progress entry for a campaign, or None."""
        try:
            with self._sync_client() as client:
                raw = client.get(self._key(campaign_id))
            return json.loads(raw) if raw else None
        except Exception as exc:
            logger.warning("ProgressTracker read failed (redis unavailable?): %s", exc)
            return None

    def delete(self, campaign_id: int) -> None:
        """Remove the progress entry for a campaign."""
        try:
            with self._sync_client() as client:
                client.delete(self._key(campaign_id))
        except Exception as exc:
            logger.warning("ProgressTracker delete failed: %s", exc)

    # ------------------------------------------------------------------
    # Async API (FastAPI endpoints)
    # ------------------------------------------------------------------
    async def get_progress_async(self, campaign_id: int) -> Optional[Dict[str, Any]]:
        """Async variant of :meth:`get_progress` for use in API endpoints."""
        try:
            client = redis_asyncio.Redis.from_url(self.redis_url, decode_responses=True)
            try:
                raw = await client.get(self._key(campaign_id))
            finally:
                await client.aclose()
            return json.loads(raw) if raw else None
        except Exception as exc:
            logger.warning("ProgressTracker async read failed (redis unavailable?): %s", exc)
            return None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _write(self, campaign_id: int, entry: Dict[str, Any]) -> None:
        try:
            payload = json.dumps(entry)
            with self._sync_client() as client:
                client.set(self._key(campaign_id), payload, ex=PROGRESS_TTL_SECONDS)
        except Exception as exc:
            logger.warning("ProgressTracker write failed (redis unavailable?): %s", exc)


# Shared instance
progress_tracker = ProgressTracker()

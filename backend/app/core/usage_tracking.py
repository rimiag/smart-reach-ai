"""
Usage Tracking

Monthly per-provider request counters for the admin API-usage dashboard.

Deliberately fail-open: a tracking problem is logged and swallowed so it can
never break the research/chat request it is measuring.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.dialects.mysql import insert as mysql_insert

from app.db.base import AsyncSessionLocal
from app.models.api_usage import ApiUsageCounter

logger = logging.getLogger(__name__)


async def bump_api_usage(provider: str) -> None:
    """
    Increment the monthly request counter for ``provider`` (e.g. "serpapi").

    Uses a MySQL/MariaDB upsert (INSERT ... ON DUPLICATE KEY UPDATE) on its own
    short-lived session so callers need no db dependency.
    """
    try:
        period = datetime.now(timezone.utc).strftime("%Y-%m")
        stmt = mysql_insert(ApiUsageCounter).values(provider=provider, period=period, count=1)
        stmt = stmt.on_duplicate_key_update(count=ApiUsageCounter.count + 1)
        async with AsyncSessionLocal() as db:
            await db.execute(stmt)
            await db.commit()
    except Exception as exc:  # fail-open by design
        logger.warning("api-usage bump failed for %s: %s", provider, exc)

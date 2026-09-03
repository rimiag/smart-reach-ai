"""
Search Tasks

Celery tasks for the search & discovery phase of a campaign (Iteration 1.4).

The core logic lives in plain async functions so the exact same code runs:

* inside a Celery worker (staging/production), via ``run_campaign_search``;
* directly on the API process event loop (laptop development without a
  Redis broker), via ``run_campaign_search_async`` dispatched by the API.

Pipeline per campaign:

    keywords -> SearchAgent (provider search -> validate -> dedupe)
             -> ResearchResult rows (one per unique domain per campaign)
             -> crawl phase (Iteration 1.5): crawl sites, extract contacts,
                create leads
             -> progress updates in Redis
             -> campaign status: researching -> ready
"""

import asyncio
import logging
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.search_agent import SearchAgent
from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.integrations.search_base import SearchProviderError, SearchResult
from app.models.campaign import Campaign
from app.models.research_result import ResearchResult
from app.tasks.celery_app import celery_app
from app.tasks.crawl_tasks import run_campaign_crawl_async
from app.tasks.progress_tracker import progress_tracker

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Core orchestration (async)
# -----------------------------------------------------------------------------
async def run_campaign_search_async(campaign_id: int) -> Dict[str, Any]:
    """
    Run the research phases for a campaign: search every keyword, then crawl
    the discovered websites (contact extraction + lead creation).

    Idempotent: re-runs skip domains already stored for the campaign.

    Raises:
        ValueError: If the campaign does not exist or has no keywords.
        SearchProviderError: If no provider is configured or every keyword
            search failed.
    """
    async with AsyncSessionLocal() as db:
        try:
            summary = await _run_search(db, campaign_id)
        except Exception as exc:
            # Leave the system in a retryable state: report the failure and
            # put the campaign back to draft so the user can start again.
            logger.exception("Search phase failed for campaign %d", campaign_id)
            await db.rollback()
            progress_tracker.fail(campaign_id, str(exc))
            await _reset_campaign_status(db, campaign_id)
            raise

    # Search session closed. Hand off to the crawl phase (Iteration 1.5) in
    # the same run - it owns finalizing campaign status and progress.
    summary["crawl"] = await run_campaign_crawl_async(campaign_id)
    return summary


async def _run_search(db: AsyncSession, campaign_id: int) -> Dict[str, Any]:
    """Search every campaign keyword and save the results."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()

    if campaign is None:
        raise ValueError(f"Campaign {campaign_id} not found")

    keywords: List[str] = list(campaign.keywords or [])
    if not keywords:
        raise ValueError(f"Campaign {campaign_id} has no keywords")

    # Raises SearchProviderError when nothing is configured - caught upstream.
    agent = SearchAgent()

    progress_tracker.initialize(
        campaign_id,
        keywords_total=len(keywords),
        current_step="Searching",
    )
    logger.info(
        "Starting search phase for campaign %d with %d keywords (%s provider)",
        campaign_id,
        len(keywords),
        agent.provider.name,
    )

    summary: Dict[str, Any] = {
        "campaign_id": campaign_id,
        "provider": agent.provider.name,
        "keywords_total": len(keywords),
        "keywords_succeeded": 0,
        "keywords_failed": 0,
        "websites_found": 0,
        "duplicates_skipped": 0,
    }

    for idx, keyword in enumerate(keywords):
        progress_tracker.set_step(
            campaign_id,
            current_step=f"Searching: {keyword}",
            progress_percentage=(idx / len(keywords)) * 100,
        )

        try:
            results = await agent.search(keyword)
        except SearchProviderError as exc:
            # One bad keyword must not sink the whole run.
            logger.error("Search failed for keyword %r: %s", keyword, exc)
            summary["keywords_failed"] += 1
            continue

        saved, skipped = await _save_research_results(
            db, campaign, keyword, results, provider_name=agent.provider.name
        )

        summary["keywords_succeeded"] += 1
        summary["websites_found"] += saved
        summary["duplicates_skipped"] += skipped

        progress_tracker.increment(campaign_id, "websites_found", saved)
        progress_tracker.update(
            campaign_id,
            keywords_completed=summary["keywords_succeeded"] + summary["keywords_failed"],
        )

        logger.info(
            "Keyword %r: %d new websites saved, %d duplicates skipped",
            keyword,
            saved,
            skipped,
        )

        # Be polite to the search provider between keywords.
        if idx < len(keywords) - 1:
            await asyncio.sleep(settings.search_per_keyword_delay)

    if summary["keywords_succeeded"] == 0:
        raise SearchProviderError(
            "All keyword searches failed - check the search provider "
            "credentials, quota and connectivity."
        )

    # Search phase done. The crawl phase (Iteration 1.5) runs next and owns
    # finalizing campaign status ('ready') and the progress tracker.
    logger.info("Search phase complete for campaign %d: %s", campaign_id, summary)

    return summary


async def _save_research_results(
    db: AsyncSession,
    campaign: Campaign,
    keyword: str,
    results: List[SearchResult],
    provider_name: str,
) -> tuple[int, int]:
    """
    Persist search results as ResearchResult rows.

    Skips domains already discovered for this campaign (across keywords and
    across re-runs).

    Returns:
        Tuple of (saved_count, skipped_count).
    """
    domains = [r.domain for r in results if r.domain]
    if not domains:
        return 0, 0

    existing = await db.execute(
        select(ResearchResult.domain).where(
            ResearchResult.campaign_id == campaign.id,
            ResearchResult.domain.in_(domains),
        )
    )
    existing_domains = set(existing.scalars().all())

    saved = 0
    for search_result in results:
        if not search_result.domain or search_result.domain in existing_domains:
            continue

        db.add(
            ResearchResult(
                campaign_id=campaign.id,
                user_id=campaign.user_id,
                keyword=keyword,
                url=search_result.url,
                domain=search_result.domain,
                title=(search_result.title or "")[:512] or None,
                snippet=search_result.snippet,
                status="discovered",
                provider=provider_name,
                result_position=search_result.position or None,
                extra_data=search_result.to_dict(),
            )
        )
        existing_domains.add(search_result.domain)
        saved += 1

    await db.commit()
    return saved, len(results) - saved


async def _reset_campaign_status(db: AsyncSession, campaign_id: int) -> None:
    """Put a researching campaign back to draft so it can be started again."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if campaign is not None and campaign.status == "researching":
        campaign.status = "draft"
        await db.commit()


# -----------------------------------------------------------------------------
# Celery task entry point (routed to the "search" queue)
# -----------------------------------------------------------------------------
@celery_app.task(
    name="app.tasks.search_tasks.run_campaign_search", time_limit=7200, soft_time_limit=7100
)
def run_campaign_search(campaign_id: int) -> Dict[str, Any]:
    """
    Celery task: run search + crawl phases for a campaign.

    Long time limits: a polite crawl of a few hundred websites takes well
    over the default 5-minute Celery limit.

    Failures are reported through the progress tracker (visible in the UI)
    and the campaign is reset to draft; the task itself is not retried since
    a re-run is triggered from the UI after the underlying cause is fixed.
    """
    logger.info("Celery: running search phase for campaign %d", campaign_id)
    return asyncio.run(run_campaign_search_async(campaign_id))

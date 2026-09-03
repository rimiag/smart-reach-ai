"""
Crawl Tasks

Crawling & extraction phase of a campaign (Iteration 1.5).

Consumes the ``research_results`` rows produced by the search phase (status
``discovered``), crawls each website politely (robots.txt + rate limits),
extracts public contact details and creates leads.

The core logic lives in plain async functions so the exact same code runs:

* inside a Celery worker, via ``crawl_campaign`` (routed to the "crawl"
  queue - also usable to re-drive a crawl without re-searching);
* chained directly after the search phase inside the same run, via
  ``run_campaign_crawl_async`` called from ``run_campaign_search_async``.

Pipeline per campaign:

    research_results (discovered)
        -> CrawlerAgent (robots check -> homepage -> contact pages -> extract)
        -> DataNormalizer (clean + dedupe)
        -> DuplicateDetector (skip existing domains/emails)
        -> LeadCreator (new leads)
        -> progress updates in Redis
        -> campaign status: researching -> ready
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.crawler_agent import CrawlerAgent
from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.models.campaign import Campaign
from app.models.research_result import ResearchResult
from app.services.data_normalizer import data_normalizer
from app.services.duplicate_detector import DuplicateDetector
from app.services.lead_creator import lead_creator
from app.tasks.celery_app import celery_app
from app.tasks.progress_tracker import progress_tracker

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Core orchestration (async)
# -----------------------------------------------------------------------------
async def run_campaign_crawl_async(campaign_id: int, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Crawl all discovered websites for a campaign and create leads.

    Idempotent-ish: only rows with status ``discovered`` are processed, so
    re-runs pick up exactly the not-yet-processed websites. Failures on
    individual websites are contained; only a catastrophic error (e.g. the
    database being down) raises.

    Raises:
        ValueError: If the campaign does not exist.
    """
    async with AsyncSessionLocal() as db:
        try:
            return await _run_crawl(db, campaign_id, limit)
        except Exception as exc:
            logger.exception("Crawl phase failed for campaign %d", campaign_id)
            await db.rollback()
            progress_tracker.update(campaign_id, error=f"Crawling failed: {exc}")
            # Do not waste the completed search: still finalize the campaign.
            await _finalize(db, campaign_id)
            raise


async def _run_crawl(db: AsyncSession, campaign_id: int, limit: Optional[int]) -> Dict[str, Any]:
    """Crawl every discovered research result and create leads."""
    campaign = (
        await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    ).scalar_one_or_none()
    if campaign is None:
        raise ValueError(f"Campaign {campaign_id} not found")

    query = (
        select(ResearchResult)
        .where(ResearchResult.campaign_id == campaign_id)
        .where(ResearchResult.status == "discovered")
        .order_by(ResearchResult.id)
    )
    if limit:
        query = query.limit(limit)
    results = (await db.execute(query)).scalars().all()

    summary: Dict[str, Any] = {
        "campaign_id": campaign_id,
        "websites_to_crawl": len(results),
        "websites_crawled": 0,
        "contacts_found": 0,
        "leads_created": 0,
        "duplicates_skipped": 0,
        "robots_blocked": 0,
        "failed": 0,
    }

    if not results:
        logger.info("Crawl phase for campaign %d: nothing discovered to crawl", campaign_id)
        await _finalize(db, campaign_id)
        return summary

    total = len(results)
    progress_tracker.set_step(campaign_id, f"Crawling 0/{total} websites", 90.0)
    logger.info("Crawling %d websites for campaign %d", total, campaign_id)

    # Network phase: concurrent crawling, no DB access inside the coroutines.
    async with CrawlerAgent() as agent:
        semaphore = asyncio.Semaphore(settings.crawler_max_workers)

        async def process(site: ResearchResult):
            async with semaphore:
                try:
                    return site, *(await agent.process_website(site.url))
                except Exception as exc:
                    logger.error("Crawl of %s crashed: %s", site.url, exc)
                    return site, "failed", None, str(exc)

        outcomes = await asyncio.gather(*(process(site) for site in results))

    # DB phase: sequential writes with progress updates.
    detector = await DuplicateDetector.create(db, campaign_id)
    processed = 0

    for site, status, contact, error in outcomes:
        processed += 1
        site.status = status
        site.error_message = error or None
        site.crawled_at = datetime.utcnow()

        if status == "crawled" and contact is not None and (contact.emails or contact.phones):
            normalized = data_normalizer.normalize(contact, fallback_domain=site.domain)

            if detector.is_duplicate(normalized.website, tuple(normalized.emails)):
                site.status = "skipped"
                site.error_message = "duplicate: campaign already has a lead for this domain/email"
                summary["duplicates_skipped"] += 1
            else:
                lead = await lead_creator.create_from_contact_info(db, site, normalized)
                if lead is not None:
                    summary["leads_created"] += 1
                    progress_tracker.increment(campaign_id, "leads_created", 1)
                    # Keep the index current: a second website of the same
                    # organization later in this run must also be skipped.
                    detector.add_identity(normalized.website, tuple(normalized.emails))
                summary["contacts_found"] += 1
                progress_tracker.increment(campaign_id, "contacts_found", 1)

        if status == "crawled":
            summary["websites_crawled"] += 1
            progress_tracker.increment(campaign_id, "websites_crawled", 1)
        elif status == "skipped":
            if "robots" in (error or ""):
                summary["robots_blocked"] += 1
            else:
                summary["duplicates_skipped"] += 1
        elif status == "failed":
            summary["failed"] += 1

        progress_tracker.set_step(
            campaign_id,
            f"Crawling {processed}/{total} websites",
            90.0 + (processed / total) * 10.0,
        )
        await db.commit()

    await _finalize(db, campaign_id)
    logger.info("Crawl phase complete for campaign %d: %s", campaign_id, summary)
    return summary


async def _finalize(db: AsyncSession, campaign_id: int) -> None:
    """Move a researching campaign to ready and mark progress complete."""
    campaign = (
        await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    ).scalar_one_or_none()
    if campaign is not None and campaign.status in ("researching", "ready"):
        campaign.status = "ready"
        await db.commit()
    progress_tracker.finish(campaign_id)


# -----------------------------------------------------------------------------
# Celery task entry point (routed to the "crawl" queue)
# -----------------------------------------------------------------------------
@celery_app.task(name="app.tasks.crawl_tasks.crawl_campaign", time_limit=7200, soft_time_limit=7100)
def crawl_campaign(campaign_id: int, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Celery task: crawl the discovered websites for a campaign.

    Long time limits: a polite crawl of a few hundred websites takes well
    over the default 5-minute Celery limit.
    """
    logger.info("Celery: running crawl phase for campaign %d", campaign_id)
    return asyncio.run(run_campaign_crawl_async(campaign_id, limit))

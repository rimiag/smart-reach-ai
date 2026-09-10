"""
Qualification Tasks

AI qualification of leads (Phase 2). Processes leads with status ``new`` and
moves successfully scored ones to ``review`` for human decision-making.

Runs in three ways:

* chained after the crawl phase inside a research run (orchestrated by
  ``run_campaign_search_async`` when ``ai_auto_qualify`` is enabled);
* standalone Celery task ``qualify_campaign`` (routed to the "ai" queue);
* synchronously per-lead from the API (single-lead qualify endpoint).

Per-lead AI failures are contained: the lead simply stays ``new`` and the run
summary counts the failure.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.qualification_agent import QualificationAgent, QualificationParseError
from app.db.base import AsyncSessionLocal
from app.integrations.ai_base import AIProviderError
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.tasks.celery_app import celery_app
from app.tasks.progress_tracker import progress_tracker

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Core orchestration (async)
# -----------------------------------------------------------------------------
async def run_campaign_qualification_async(
    campaign_id: int, limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Qualify all ``new`` leads for a campaign with the AI provider.

    Raises:
        AIProviderError: If no AI provider is configured (callers decide
            whether that is fatal - the chained research path skips silently,
            the manual endpoints return 400).
        ValueError: If the campaign does not exist.
    """
    async with AsyncSessionLocal() as db:
        return await _run_qualification(db, campaign_id, limit)


async def _run_qualification(
    db: AsyncSession, campaign_id: int, limit: Optional[int]
) -> Dict[str, Any]:
    campaign = (
        await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    ).scalar_one_or_none()
    if campaign is None:
        raise ValueError(f"Campaign {campaign_id} not found")

    query = (
        select(Lead)
        .where(Lead.campaign_id == campaign_id)
        .where(Lead.status == "new")
        .order_by(Lead.id)
    )
    if limit:
        query = query.limit(limit)
    leads = (await db.execute(query)).scalars().all()

    summary: Dict[str, Any] = {
        "campaign_id": campaign_id,
        "leads_to_qualify": len(leads),
        "qualified": 0,
        "failed": 0,
    }

    if not leads:
        logger.info("Qualification for campaign %d: no new leads to qualify", campaign_id)
        return summary

    # Raises AIProviderError when unconfigured - documented upstream behaviour.
    agent = QualificationAgent()

    total = len(leads)
    progress_tracker.set_step(campaign_id, f"Qualifying 0/{total} leads with AI", 100.0)
    logger.info(
        "Qualifying %d leads for campaign %d (%s)",
        total,
        campaign_id,
        agent.client.name,
    )

    for processed, lead in enumerate(leads, start=1):
        try:
            result = await agent.qualify(lead, campaign)
        except (AIProviderError, QualificationParseError) as exc:
            logger.error("Qualification failed for lead %d: %s", lead.id, exc)
            summary["failed"] += 1
        else:
            lead.lead_score = result.score
            reasoning = (
                f"[{result.category}] {result.reasoning}" if result.category else result.reasoning
            )
            if result.signals:
                reasoning += f" | Signals: {', '.join(result.signals)}"
            lead.ai_reasoning = reasoning
            lead.status = "review"
            lead.qualified_at = datetime.utcnow()
            summary["qualified"] += 1

        progress_tracker.set_step(
            campaign_id,
            f"Qualifying {processed}/{total} leads with AI",
            100.0,
        )
        await db.commit()

    logger.info("Qualification complete for campaign %d: %s", campaign_id, summary)
    return summary


# -----------------------------------------------------------------------------
# Celery task entry point (routed to the "ai" queue)
# -----------------------------------------------------------------------------
@celery_app.task(
    name="app.tasks.qualify_tasks.qualify_campaign", time_limit=7200, soft_time_limit=7100
)
def qualify_campaign(campaign_id: int, limit: Optional[int] = None) -> Dict[str, Any]:
    """Celery task: AI-qualify the new leads of a campaign."""
    logger.info("Celery: running AI qualification for campaign %d", campaign_id)
    return asyncio.run(run_campaign_qualification_async(campaign_id, limit))

"""
Follow-up Sequence Tasks

Phase 5: drafts AI follow-up emails for leads that were contacted but
haven't replied within the configured window (default 4 days), up to a
maximum number of follow-ups per lead.

Follow-ups always route back through the human approval flow: the lead
returns to ``review`` with a fresh draft, and sending happens only through
the explicit Review & Send workflow. Never automatic.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.email_agent import EmailGenerationAgent, EmailParseError
from app.core.config import settings
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
async def run_followup_sweep_async(campaign_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Draft follow-up emails for eligible silent leads.

    Eligible: status ``sent``, no reply received, last email older than
    ``follow_up_after_days``, fewer than ``follow_up_max_count`` follow-ups
    already drafted. Drafted leads return to ``review`` for approval.

    Args:
        campaign_id: Limit the sweep to one campaign; None sweeps all.

    Raises:
        AIProviderError: If no AI provider is configured.
    """
    async with AsyncSessionLocal() as db:
        return await _run_sweep(db, campaign_id)


async def _run_sweep(db: AsyncSession, campaign_id: Optional[int]) -> Dict[str, Any]:
    cutoff = datetime.utcnow() - timedelta(days=settings.follow_up_after_days)

    query = (
        select(Lead)
        .where(Lead.status == "sent")
        .where(Lead.generated_email.is_not(None))
        .where(Lead.last_emailed_at.is_not(None))
        .where(Lead.last_emailed_at <= cutoff)
        .where(Lead.follow_up_count < settings.follow_up_max_count)
        .order_by(Lead.lead_score.desc())
    )
    if campaign_id:
        query = query.where(Lead.campaign_id == campaign_id)
    leads = (await db.execute(query)).scalars().all()

    summary: Dict[str, Any] = {
        "campaign_id": campaign_id or "all",
        "leads_eligible": len(leads),
        "follow_ups_drafted": 0,
        "failed": 0,
    }

    if not leads:
        logger.info("Follow-up sweep: no eligible leads")
        return summary

    agent = EmailGenerationAgent()
    total = len(leads)
    logger.info("Follow-up sweep: drafting %d follow-up(s)", total)

    if campaign_id:
        progress_tracker.set_step(campaign_id, f"Drafting {total} follow-up(s)", 100.0)

    for index, lead in enumerate(leads, start=1):
        campaign = lead.campaign
        try:
            draft = await agent.generate_follow_up(
                lead, campaign, follow_up_number=lead.follow_up_count + 1
            )
        except (AIProviderError, EmailParseError) as exc:
            logger.error("Follow-up generation failed for lead %d: %s", lead.id, exc)
            summary["failed"] += 1
            continue

        lead.generated_email = f"Subject: {draft.subject}\n\n{draft.body}"
        lead.follow_up_count += 1
        lead.status = "review"  # back to the human decision queue
        summary["follow_ups_drafted"] += 1

        if campaign_id:
            progress_tracker.set_step(campaign_id, f"Drafting {index}/{total} follow-up(s)", 100.0)
        if index % 5 == 0:
            await db.commit()

    await db.commit()
    logger.info("Follow-up sweep complete: %s", summary)
    return summary


# -----------------------------------------------------------------------------
# Celery task entry point (daily beat + on-demand dispatch)
# -----------------------------------------------------------------------------
@celery_app.task(
    name="app.tasks.followup_tasks.followup_sweep", time_limit=7200, soft_time_limit=7100
)
def followup_sweep(campaign_id: Optional[int] = None) -> Dict[str, Any]:
    """Celery task: draft follow-ups for eligible silent leads."""
    logger.info("Celery: running follow-up sweep")
    return asyncio.run(run_followup_sweep_async(campaign_id))

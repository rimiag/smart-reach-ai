"""
Email Generation Tasks

AI generation of personalized outreach emails (Phase 2). Drafts are stored on
the lead's ``generated_email`` field and always await human review - nothing
is sent automatically (that is Phase 3 with an explicit approval workflow).

Runs chained after qualification (research pipeline), as the standalone
Celery task ``generate_campaign_emails``, or synchronously per-lead from the
API (regenerate endpoint).
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.email_agent import EmailGenerationAgent, EmailParseError
from app.db.base import AsyncSessionLocal
from app.integrations.ai_base import AIProviderError
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.services.template_service import template_service
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Leads eligible for email drafts: reviewed (or approved) and not yet drafted.
ELIGIBLE_STATUSES = ("review", "approved")


# -----------------------------------------------------------------------------
# Core orchestration (async)
# -----------------------------------------------------------------------------
async def run_campaign_email_generation_async(
    campaign_id: int, limit: Optional[int] = None, regenerate: bool = False
) -> Dict[str, Any]:
    """
    Generate outreach email drafts for a campaign's review-ready leads.

    Args:
        campaign_id: Campaign whose leads get drafts.
        limit: Optional maximum number of leads to process.
        regenerate: When False (default) leads that already have a draft are
            skipped; when True existing drafts are replaced.

    Raises:
        AIProviderError: If no AI provider is configured.
        ValueError: If the campaign does not exist.
    """
    async with AsyncSessionLocal() as db:
        return await _run_email_generation(db, campaign_id, limit, regenerate)


async def _run_email_generation(
    db: AsyncSession, campaign_id: int, limit: Optional[int], regenerate: bool
) -> Dict[str, Any]:
    campaign = (
        await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    ).scalar_one_or_none()
    if campaign is None:
        raise ValueError(f"Campaign {campaign_id} not found")

    query = (
        select(Lead)
        .where(Lead.campaign_id == campaign_id)
        .where(Lead.status.in_(ELIGIBLE_STATUSES))
        .order_by(Lead.lead_score.desc(), Lead.id)
    )
    if not regenerate:
        query = query.where(Lead.generated_email.is_(None))
    if limit:
        query = query.limit(limit)
    leads = (await db.execute(query)).scalars().all()

    summary: Dict[str, Any] = {
        "campaign_id": campaign_id,
        "leads_to_process": len(leads),
        "emails_generated": 0,
        "failed": 0,
    }

    if not leads:
        logger.info("Email generation for campaign %d: no eligible leads", campaign_id)
        return summary

    agent = EmailGenerationAgent()
    total = len(leads)
    logger.info(
        "Generating emails for %d leads of campaign %d (%s)",
        total,
        campaign_id,
        agent.client.name,
    )

    for index, lead in enumerate(leads):
        template_hint = template_service.render(
            template_service.get_template(template_service.pick_for_index(index)),
            {"ORGANIZATION_NAME": lead.organization_name},
        )

        try:
            draft = await agent.generate(lead, campaign, template_hint=template_hint)
        except (AIProviderError, EmailParseError) as exc:
            logger.error("Email generation failed for lead %d: %s", lead.id, exc)
            summary["failed"] += 1
            continue

        lead.generated_email = f"Subject: {draft.subject}\n\n{draft.body}"
        summary["emails_generated"] += 1

        if (index + 1) % 5 == 0:  # periodic commit keeps progress durable
            await db.commit()

    await db.commit()
    logger.info("Email generation complete for campaign %d: %s", campaign_id, summary)
    return summary


# -----------------------------------------------------------------------------
# Celery task entry point (default queue)
# -----------------------------------------------------------------------------
@celery_app.task(
    name="app.tasks.email_tasks.generate_campaign_emails", time_limit=7200, soft_time_limit=7100
)
def generate_campaign_emails(
    campaign_id: int, limit: Optional[int] = None, regenerate: bool = False
) -> Dict[str, Any]:
    """Celery task: generate email drafts for a campaign's review-ready leads."""
    logger.info("Celery: generating emails for campaign %d", campaign_id)
    return asyncio.run(run_campaign_email_generation_async(campaign_id, limit, regenerate))

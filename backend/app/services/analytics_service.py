"""
Analytics Service

Campaign statistics and dashboard aggregates (Iteration 1.6).

Email open/click tracking does not exist yet (Phase 4); those counters are
computed from lead statuses where possible and otherwise stay zero until the
tracking infrastructure lands.
"""

import logging
from typing import List

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.research_result import ResearchResult
from app.schemas.campaign import CampaignComparison, CampaignStats, DashboardStats

logger = logging.getLogger(__name__)

# Statuses that count as "qualified / awaiting human decision" (Phase 2 fills these).
QUALIFIED_STATUSES = ("qualified", "review")


class AnalyticsService:
    """Statistics for campaigns and user dashboards."""

    # ------------------------------------------------------------------
    # Per-campaign statistics
    # ------------------------------------------------------------------
    async def get_campaign_stats(self, db: AsyncSession, campaign_id: int) -> CampaignStats:
        """Compute full statistics for one campaign."""

        async def count_leads(*conditions) -> int:
            query = select(func.count(Lead.id)).where(Lead.campaign_id == campaign_id, *conditions)
            return (await db.execute(query)).scalar() or 0

        async def count_research(*conditions) -> int:
            query = select(func.count(ResearchResult.id)).where(
                ResearchResult.campaign_id == campaign_id, *conditions
            )
            return (await db.execute(query)).scalar() or 0

        websites_found = await count_research()
        websites_crawled = await count_research(ResearchResult.status == "crawled")

        leads_created = await count_leads()
        contacts_found = await count_leads(or_(Lead.email.is_not(None), Lead.phone.is_not(None)))
        leads_qualified = await count_leads(Lead.status.in_(QUALIFIED_STATUSES))
        emails_sent = (
            await db.execute(
                select(func.coalesce(func.sum(Lead.emails_sent), 0)).where(
                    Lead.campaign_id == campaign_id
                )
            )
        ).scalar() or 0
        emails_delivered = await count_leads(Lead.emails_sent > 0, Lead.status != "bounced")
        replies_received = await count_leads(Lead.status == "replied")
        interested = await count_leads(Lead.status == "interested")
        unsubscribes = await count_leads(Lead.status == "unsubscribed")
        bounces = await count_leads(Lead.status == "bounced")

        return CampaignStats(
            websites_found=websites_found,
            websites_crawled=websites_crawled,
            contacts_found=contacts_found,
            leads_created=leads_created,
            leads_qualified=leads_qualified,
            emails_sent=emails_sent,
            emails_delivered=emails_delivered,
            emails_opened=0,  # open tracking arrives with Phase 4
            replies_received=replies_received,
            interested_leads=interested,
            unsubscribes=unsubscribes,
            bounces=bounces,
        )

    # ------------------------------------------------------------------
    # Dashboard (all campaigns of a user)
    # ------------------------------------------------------------------
    async def get_dashboard_stats(self, db: AsyncSession, user_id: int) -> DashboardStats:
        """Aggregate statistics across all of a user's campaigns."""

        async def count(model: type, *conditions) -> int:
            query = select(func.count(model.id)).where(*conditions)
            return (await db.execute(query)).scalar() or 0

        return DashboardStats(
            campaigns_total=await count(Campaign, Campaign.user_id == user_id),
            campaigns_active=await count(
                Campaign,
                Campaign.user_id == user_id,
                Campaign.status.in_(("researching", "active")),
            ),
            leads_total=await count(Lead, Lead.user_id == user_id),
            leads_new=await count(Lead, Lead.user_id == user_id, Lead.status == "new"),
            leads_approved=await count(Lead, Lead.user_id == user_id, Lead.status == "approved"),
            leads_rejected=await count(Lead, Lead.user_id == user_id, Lead.status == "rejected"),
            websites_discovered=await count(ResearchResult, ResearchResult.user_id == user_id),
            websites_crawled=await count(
                ResearchResult,
                ResearchResult.user_id == user_id,
                ResearchResult.status == "crawled",
            ),
        )

    # ------------------------------------------------------------------
    # Per-campaign comparison rows
    # ------------------------------------------------------------------
    async def get_campaign_comparison(
        self, db: AsyncSession, user_id: int
    ) -> List[CampaignComparison]:
        """One summary row per campaign, newest first."""
        campaigns = (
            (
                await db.execute(
                    select(Campaign)
                    .where(Campaign.user_id == user_id)
                    .order_by(Campaign.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        if not campaigns:
            return []

        lead_rows = (
            await db.execute(
                select(
                    Lead.campaign_id,
                    Lead.status,
                    func.count(Lead.id),
                )
                .where(Lead.user_id == user_id)
                .group_by(Lead.campaign_id, Lead.status)
            )
        ).all()
        research_rows = (
            await db.execute(
                select(ResearchResult.campaign_id, func.count(ResearchResult.id))
                .where(ResearchResult.user_id == user_id)
                .group_by(ResearchResult.campaign_id)
            )
        ).all()

        leads_by_campaign: dict = {}
        for campaign_id, lead_status, count in lead_rows:
            stats = leads_by_campaign.setdefault(campaign_id, {"total": 0, "new": 0, "approved": 0})
            stats["total"] += count
            if lead_status == "new":
                stats["new"] += count
            elif lead_status == "approved":
                stats["approved"] += count

        discovered_by_campaign = {row[0]: row[1] for row in research_rows}

        return [
            CampaignComparison(
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                status=campaign.status,
                leads_total=leads_by_campaign.get(campaign.id, {}).get("total", 0),
                leads_new=leads_by_campaign.get(campaign.id, {}).get("new", 0),
                leads_approved=leads_by_campaign.get(campaign.id, {}).get("approved", 0),
                websites_discovered=discovered_by_campaign.get(campaign.id, 0),
                created_at=campaign.created_at,
            )
            for campaign in campaigns
        ]


analytics_service = AnalyticsService()

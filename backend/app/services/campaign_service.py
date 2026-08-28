"""
Campaign Service

Business logic for campaign management.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.schemas.campaign import CampaignCreate, CampaignUpdate


class CampaignService:
    """Service for managing campaigns."""

    @staticmethod
    async def create_campaign(
        db: AsyncSession,
        user_id: int,
        campaign_data: CampaignCreate,
    ) -> Campaign:
        """
        Create a new campaign.

        Args:
            db: Database session
            user_id: ID of the user creating the campaign
            campaign_data: Campaign creation data

        Returns:
            Campaign: Created campaign
        """
        new_campaign = Campaign(
            user_id=user_id,
            name=campaign_data.name,
            description=campaign_data.description,
            keywords=campaign_data.keywords,
        )

        db.add(new_campaign)
        await db.commit()
        await db.refresh(new_campaign)

        return new_campaign

    @staticmethod
    async def get_campaign(db: AsyncSession, campaign_id: int) -> Optional[Campaign]:
        """
        Get a campaign by ID.

        Args:
            db: Database session
            campaign_id: Campaign ID

        Returns:
            Campaign or None
        """
        result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_campaigns(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Campaign], int]:
        """
        Get all campaigns for a user.

        Args:
            db: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (campaigns list, total count)
        """
        # Get total count
        from sqlalchemy import func

        count_result = await db.execute(
            select(func.count(Campaign.id)).where(Campaign.user_id == user_id)
        )
        total = count_result.scalar() or 0

        # Get campaigns
        result = await db.execute(
            select(Campaign)
            .where(Campaign.user_id == user_id)
            .order_by(Campaign.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        campaigns = result.scalars().all()

        return list(campaigns), total

    @staticmethod
    async def update_campaign(
        db: AsyncSession,
        campaign: Campaign,
        campaign_data: CampaignUpdate,
    ) -> Campaign:
        """
        Update a campaign.

        Args:
            db: Database session
            campaign: Existing campaign
            campaign_data: Update data

        Returns:
            Campaign: Updated campaign
        """
        if campaign_data.name is not None:
            campaign.name = campaign_data.name
        if campaign_data.description is not None:
            campaign.description = campaign_data.description
        if campaign_data.keywords is not None:
            campaign.keywords = campaign_data.keywords
        if campaign_data.settings is not None:
            campaign.settings = campaign_data.settings

        await db.commit()
        await db.refresh(campaign)

        return campaign

    @staticmethod
    async def delete_campaign(db: AsyncSession, campaign: Campaign) -> None:
        """
        Delete a campaign.

        Args:
            db: Database session
            campaign: Campaign to delete
        """
        await db.delete(campaign)
        await db.commit()

    @staticmethod
    async def update_status(
        db: AsyncSession,
        campaign: Campaign,
        status: str,
    ) -> Campaign:
        """
        Update campaign status.

        Args:
            db: Database session
            campaign: Campaign to update
            status: New status

        Returns:
            Campaign: Updated campaign
        """
        campaign.status = status

        if status == "researching" and campaign.started_at is None:
            campaign.started_at = datetime.utcnow()
        elif status == "completed" and campaign.completed_at is None:
            campaign.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(campaign)

        return campaign


campaign_service = CampaignService()

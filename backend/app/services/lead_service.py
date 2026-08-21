"""
Lead Service

Business logic for lead management.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lead import Lead
from app.schemas.lead import BulkActionRequest, LeadCreate, LeadUpdate


class LeadService:
    """Service for managing leads."""

    @staticmethod
    async def create_lead(
        db: AsyncSession,
        user_id: int,
        lead_data: LeadCreate,
    ) -> Lead:
        """
        Create a new lead.

        Args:
            db: Database session
            user_id: ID of the user creating the lead
            lead_data: Lead creation data

        Returns:
            Lead: Created lead
        """
        new_lead = Lead(
            user_id=user_id,
            campaign_id=lead_data.campaign_id,
            keyword=lead_data.keyword,
            source_url=lead_data.source_url,
            contact_page_url=lead_data.contact_page_url,
            organization_name=lead_data.organization_name,
            website=lead_data.website,
            contact_name=lead_data.contact_name,
            job_title=lead_data.job_title,
            department=lead_data.department,
            email=lead_data.email,
            phone=lead_data.phone,
            country=lead_data.country,
            city=lead_data.city,
            lead_score=lead_data.lead_score,
            ai_reasoning=lead_data.ai_reasoning,
            status='new',
        )

        db.add(new_lead)
        await db.commit()
        await db.refresh(new_lead)

        return new_lead

    @staticmethod
    async def get_lead(db: AsyncSession, lead_id: int) -> Optional[Lead]:
        """
        Get a lead by ID with campaign relationship.

        Args:
            db: Database session
            lead_id: Lead ID

        Returns:
            Lead or None
        """
        result = await db.execute(
            select(Lead)
            .options(selectinload(Lead.campaign))
            .where(Lead.id == lead_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_campaign_leads(
        db: AsyncSession,
        campaign_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None,
    ) -> tuple[list[Lead], int]:
        """
        Get all leads for a campaign with filtering and pagination.

        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: User ID (for ownership verification)
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter
            min_score: Optional minimum lead score
            max_score: Optional maximum lead score

        Returns:
            Tuple of (leads list, total count)
        """
        # Build base query
        query = select(Lead).where(
            Lead.campaign_id == campaign_id,
            Lead.user_id == user_id
        )

        # Apply filters
        if status:
            query = query.where(Lead.status == status)
        if min_score is not None:
            query = query.where(Lead.lead_score >= min_score)
        if max_score is not None:
            query = query.where(Lead.lead_score <= max_score)

        # Get total count
        count_query = select(func.count(Lead.id)).where(
            Lead.campaign_id == campaign_id,
            Lead.user_id == user_id
        )
        if status:
            count_query = count_query.where(Lead.status == status)
        if min_score is not None:
            count_query = count_query.where(Lead.lead_score >= min_score)
        if max_score is not None:
            count_query = count_query.where(Lead.lead_score <= max_score)

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # Get leads with ordering
        query = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        leads = result.scalars().all()

        return list(leads), total

    @staticmethod
    async def update_lead(
        db: AsyncSession,
        lead: Lead,
        lead_data: LeadUpdate,
    ) -> Lead:
        """
        Update a lead.

        Args:
            db: Database session
            lead: Existing lead
            lead_data: Update data

        Returns:
            Lead: Updated lead
        """
        if lead_data.organization_name is not None:
            lead.organization_name = lead_data.organization_name
        if lead_data.website is not None:
            lead.website = lead_data.website
        if lead_data.email is not None:
            lead.email = lead_data.email
        if lead_data.phone is not None:
            lead.phone = lead_data.phone
        if lead_data.contact_name is not None:
            lead.contact_name = lead_data.contact_name
        if lead_data.job_title is not None:
            lead.job_title = lead_data.job_title
        if lead_data.department is not None:
            lead.department = lead_data.department
        if lead_data.country is not None:
            lead.country = lead_data.country
        if lead_data.city is not None:
            lead.city = lead_data.city

        await db.commit()
        await db.refresh(lead)

        return lead

    @staticmethod
    async def delete_lead(db: AsyncSession, lead: Lead) -> None:
        """
        Delete a lead.

        Args:
            db: Database session
            lead: Lead to delete
        """
        await db.delete(lead)
        await db.commit()

    @staticmethod
    async def approve_lead(
        db: AsyncSession,
        lead: Lead,
    ) -> Lead:
        """
        Approve a lead for outreach.

        Args:
            db: Database session
            lead: Lead to approve

        Returns:
            Lead: Updated lead
        """
        lead.status = 'approved'
        lead.approved_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(lead)

        return lead

    @staticmethod
    async def reject_lead(
        db: AsyncSession,
        lead: Lead,
    ) -> Lead:
        """
        Reject a lead.

        Args:
            db: Database session
            lead: Lead to reject

        Returns:
            Lead: Updated lead
        """
        lead.status = 'rejected'

        await db.commit()
        await db.refresh(lead)

        return lead

    @staticmethod
    async def bulk_approve(
        db: AsyncSession,
        lead_ids: list[int],
        user_id: int,
    ) -> dict:
        """
        Bulk approve multiple leads.

        Args:
            db: Database session
            lead_ids: List of lead IDs to approve
            user_id: User ID for ownership verification

        Returns:
            Dict with success_count, failed_count, errors
        """
        from app.schemas.lead import BulkActionResponse

        success_count = 0
        failed_count = 0
        errors = []

        for lead_id in lead_ids:
            try:
                result = await db.execute(
                    select(Lead).where(
                        Lead.id == lead_id,
                        Lead.user_id == user_id
                    )
                )
                lead = result.scalar_one_or_none()

                if not lead:
                    failed_count += 1
                    errors.append(f"Lead {lead_id} not found")
                    continue

                if lead.status in ['approved', 'rejected', 'sent']:
                    failed_count += 1
                    errors.append(f"Lead {lead_id} has status '{lead.status}' and cannot be approved")
                    continue

                lead.status = 'approved'
                lead.approved_at = datetime.now(timezone.utc)
                success_count += 1

            except Exception as e:
                failed_count += 1
                errors.append(f"Lead {lead_id}: {str(e)}")

        await db.commit()

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors
        }

    @staticmethod
    async def bulk_reject(
        db: AsyncSession,
        lead_ids: list[int],
        user_id: int,
    ) -> dict:
        """
        Bulk reject multiple leads.

        Args:
            db: Database session
            lead_ids: List of lead IDs to reject
            user_id: User ID for ownership verification

        Returns:
            Dict with success_count, failed_count, errors
        """
        success_count = 0
        failed_count = 0
        errors = []

        for lead_id in lead_ids:
            try:
                result = await db.execute(
                    select(Lead).where(
                        Lead.id == lead_id,
                        Lead.user_id == user_id
                    )
                )
                lead = result.scalar_one_or_none()

                if not lead:
                    failed_count += 1
                    errors.append(f"Lead {lead_id} not found")
                    continue

                if lead.status in ['approved', 'rejected', 'sent']:
                    failed_count += 1
                    errors.append(f"Lead {lead_id} has status '{lead.status}' and cannot be rejected")
                    continue

                lead.status = 'rejected'
                success_count += 1

            except Exception as e:
                failed_count += 1
                errors.append(f"Lead {lead_id}: {str(e)}")

        await db.commit()

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors
        }


lead_service = LeadService()
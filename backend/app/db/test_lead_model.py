"""
Test Lead Model - Database Connection and Model Verification

Tests the Lead model, relationships, and database operations.
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.base import AsyncSessionLocal
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.user import User


async def test_lead_model():
    """Test Lead model creation and relationships."""
    print("=" * 60)
    print("Iteration 1.3 - Lead Model Test")
    print("=" * 60)

    try:
        async with AsyncSessionLocal() as db:
            # 1. Get or create test user
            print("\n[1] Checking for test user...")
            result = await db.execute(select(User).where(User.email == "test@example.com"))
            user = result.scalar_one_or_none()

            if not user:
                from app.core.security import get_password_hash

                user = User(
                    email="test@example.com",
                    password_hash=get_password_hash("password123"),
                    name="Test User",
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                print("   ✅ Test user created")
            else:
                print("   ✅ Test user found")

            # 2. Create a test campaign
            print("\n[2] Creating test campaign...")
            campaign = Campaign(
                user_id=user.id,
                name="Test Campaign",
                description="Campaign for testing leads",
                keywords=["REDCap", "clinical research", "healthcare"],
                status="draft",
            )
            db.add(campaign)
            await db.commit()
            await db.refresh(campaign)
            print(f"   ✅ Campaign created (ID: {campaign.id})")

            # 3. Create a test lead
            print("\n[3] Creating test lead...")
            lead = Lead(
                campaign_id=campaign.id,
                user_id=user.id,
                keyword="REDCap",
                source_url="https://example.edu/research",
                contact_page_url="https://example.edu/contact",
                organization_name="Test University Research Center",
                website="https://example.edu",
                contact_name="Dr. Jane Smith",
                job_title="Research Director",
                department="Clinical Research",
                email="jane.smith@example.edu",
                phone="+1-555-0100",
                country="USA",
                city="Boston",
                lead_score=85,
                ai_reasoning="University research department with REDCap implementation",
                status="new",
            )
            db.add(lead)
            await db.commit()
            await db.refresh(lead)
            print(f"   ✅ Lead created (ID: {lead.id})")

            # 4. Read back the lead
            print("\n[4] Reading lead back...")
            result = await db.execute(
                select(Lead).options(selectinload(Lead.campaign)).where(Lead.id == lead.id)
            )
            retrieved_lead = result.scalar_one_or_none()

            if retrieved_lead:
                print(f"   ✅ Lead retrieved successfully")
                print(f"      Organization: {retrieved_lead.organization_name}")
                print(f"      Contact: {retrieved_lead.contact_name}")
                print(f"      Email: {retrieved_lead.email}")
                print(f"      Score: {retrieved_lead.lead_score}")
                print(f"      Status: {retrieved_lead.status}")
                print(f"      Campaign: {retrieved_lead.campaign.name}")

            # 5. Test lead update
            print("\n[5] Testing lead update...")
            retrieved_lead.status = "qualified"
            retrieved_lead.qualified_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(retrieved_lead)
            print(f"   ✅ Lead updated - Status: {retrieved_lead.status}")

            # 6. Test lead approval
            print("\n[6] Testing lead approval...")
            retrieved_lead.status = "approved"
            retrieved_lead.approved_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(retrieved_lead)
            print(f"   ✅ Lead approved - Status: {retrieved_lead.status}")

            # 7. Test campaign relationship
            print("\n[7] Testing campaign relationship...")
            result = await db.execute(
                select(Campaign)
                .options(selectinload(Campaign.leads))
                .where(Campaign.id == campaign.id)
            )
            campaign_with_leads = result.scalar_one_or_none()
            lead_count = len(campaign_with_leads.leads) if campaign_with_leads else 0
            print(f"   ✅ Campaign has {lead_count} lead(s)")

            # Cleanup
            print("\n[8] Cleanup...")
            await db.delete(lead)
            await db.delete(campaign)
            await db.commit()
            print("   ✅ Test data cleaned up")

            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED - Iteration 1.3 Lead Model Working!")
            print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_lead_model())

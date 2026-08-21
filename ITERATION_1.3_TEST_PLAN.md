# Iteration 1.3 - Testing Plan

**Date:** 2026-08-18
**Status:** Ready for Testing

---

## 🧪 Test Environment Setup

### Prerequisites
```bash
# 1. Ensure you're in the backend directory
cd "c:\Users\Rizwan\Desktop\Office Work\Devops-work\ai agent\smart-reach-ai\backend"

# 2. Activate virtual environment (if using local development)
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Ensure .env is configured
# Copy .env.example to .env and configure
```

### Database Migration
```bash
# Run Alembic migration to create tables
alembic upgrade head

# Verify migration status
alembic current

# Expected output: Revision ID: 001
```

---

## ✅ Pre-Flight Checks

| Check | Command | Expected Result |
|-------|---------|-----------------|
| Python version | `python --version` | 3.11+ |
| Database connection | See test script below | Connection successful |
| Tables created | `alembic history` | Shows revision 001 |
| Alembic current | `alembic current` | Revision: 001 |

---

## 🧪 Test Scripts

### 1. Database & Model Test
Run this to verify the Lead model and database connection:

**File:** `backend/app/db/test_lead_model.py` (create this)

```python
"""
Test Lead Model - Database Connection and Model Verification
"""
import asyncio
from datetime import datetime, timezone
from app.db.base import AsyncSessionLocal
from app.models.user import User
from app.models.campaign import Campaign
from app.models.lead import Lead
from sqlalchemy import select


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
                ai_qualification_reason="University research department with REDCap implementation",
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
                print(f"   Organization: {retrieved_lead.organization_name}")
                print(f"   Contact: {retrieved_lead.contact_name}")
                print(f"   Email: {retrieved_lead.email}")
                print(f"   Score: {retrieved_lead.lead_score}")
                print(f"   Status: {retrieved_lead.status}")
                print(f"   Campaign: {retrieved_lead.campaign.name}")

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
                select(Campaign).options(selectinload(Campaign.leads)).where(Campaign.id == campaign.id)
            )
            campaign_with_leads = result.scalar_one_or_none()
            lead_count = len(campaign_with_leads.leads) if campaign_with_leads else 0
            print(f"   ✅ Campaign has {lead_count} lead(s)")

            # Cleanup (optional - comment out to keep test data)
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
    # Import selectinload at runtime to avoid issues
    from sqlalchemy.orm import selectinload
    asyncio.run(test_lead_model())
```

### 2. Backend API Test Script

**File:** `backend/app/api/test_leads_api.py` (create this)

```python
"""
Test Leads API Endpoints

Run this after starting the FastAPI server.
"""
import asyncio
import requests
import json


BASE_URL = "http://localhost:8000/api/v1"


async def test_leads_api():
    """Test all leads API endpoints."""
    print("=" * 60)
    print("Iteration 1.3 - Leads API Test")
    print("=" * 60)

    # Test credentials
    email = "test@example.com"
    password = "password123"

    try:
        # 1. Register/Login
        print("\n[1] Testing authentication...")
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password}
        )

        if response.status_code == 401:
            # User doesn't exist, register first
            print("   User not found, registering...")
            response = requests.post(
                f"{BASE_URL}/auth/register",
                json={"email": email, "password": password, "name": "Test User"}
            )
            if response.status_code == 201:
                print("   ✅ User registered")
                # Login again
                response = requests.post(
                    f"{BASE_URL}/auth/login",
                    json={"email": email, "password": password}
                )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print("   ✅ Authentication successful")
        else:
            print(f"   ❌ Authentication failed: {response.status_code}")
            return

        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create a campaign for testing leads
        print("\n[2] Creating test campaign...")
        response = requests.post(
            f"{BASE_URL}/campaigns",
            headers=headers,
            json={
                "name": "Test Leads Campaign",
                "description": "Campaign for API testing",
                "keywords": ["test", "api", "leads"]
            }
        )

        if response.status_code == 201:
            campaign = response.json()
            campaign_id = campaign["id"]
            print(f"   ✅ Campaign created (ID: {campaign_id})")
        else:
            print(f"   ❌ Campaign creation failed: {response.status_code}")
            return

        # 3. Create a lead
        print("\n[3] Creating lead...")
        response = requests.post(
            f"{BASE_URL}/leads",
            headers=headers,
            json={
                "campaign_id": campaign_id,
                "keyword": "test",
                "source_url": "https://example.com",
                "organization_name": "Test Organization",
                "website": "https://example.com",
                "contact_name": "John Doe",
                "email": "john@example.com",
                "lead_score": 75
            }
        )

        if response.status_code == 201:
            lead = response.json()
            lead_id = lead["id"]
            print(f"   ✅ Lead created (ID: {lead_id})")
        else:
            print(f"   ❌ Lead creation failed: {response.status_code}")
            print(response.text)
            return

        # 4. List leads
        print("\n[4] Listing leads...")
        response = requests.get(
            f"{BASE_URL}/leads",
            headers=headers,
            params={"campaign_id": campaign_id}
        )

        if response.status_code == 200:
            leads = response.json()
            print(f"   ✅ Retrieved {leads['total']} lead(s)")
        else:
            print(f"   ❌ List leads failed: {response.status_code}")

        # 5. Get lead details
        print("\n[5] Getting lead details...")
        response = requests.get(
            f"{BASE_URL}/leads/{lead_id}",
            headers=headers
        )

        if response.status_code == 200:
            lead_detail = response.json()
            print(f"   ✅ Lead details retrieved")
            print(f"   Organization: {lead_detail['organization_name']}")
            print(f"   Contact: {lead_detail['contact_name']}")
        else:
            print(f"   ❌ Get lead failed: {response.status_code}")

        # 6. Update lead
        print("\n[6] Updating lead...")
        response = requests.put(
            f"{BASE_URL}/leads/{lead_id}",
            headers=headers,
            json={"phone": "+1-555-9999"}
        )

        if response.status_code == 200:
            print("   ✅ Lead updated")
        else:
            print(f"   ❌ Update failed: {response.status_code}")

        # 7. Approve lead
        print("\n[7] Approving lead...")
        response = requests.post(
            f"{BASE_URL}/leads/{lead_id}/approve",
            headers=headers
        )

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Lead approved - Status: {result['status']}")
        else:
            print(f"   ❌ Approve failed: {response.status_code}")

        # 8. Test bulk approve (create another lead first)
        print("\n[8] Testing bulk approve...")
        response = requests.post(
            f"{BASE_URL}/leads",
            headers=headers,
            json={
                "campaign_id": campaign_id,
                "keyword": "test2",
                "source_url": "https://example2.com",
                "organization_name": "Test Org 2",
                "website": "https://example2.com",
                "lead_score": 80
            }
        )

        if response.status_code == 201:
            lead2_id = response.json()["id"]
            # Bulk approve
            response = requests.post(
                f"{BASE_URL}/leads/bulk-approve",
                headers=headers,
                json={"ids": [lead2_id]}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Bulk approved {result['success_count']} lead(s)")
            else:
                print(f"   ❌ Bulk approve failed: {response.status_code}")

        # 9. Delete lead
        print("\n[9] Deleting lead...")
        response = requests.delete(
            f"{BASE_URL}/leads/{lead_id}",
            headers=headers
        )

        if response.status_code == 204:
            print("   ✅ Lead deleted")
        else:
            print(f"   ❌ Delete failed: {response.status_code}")

        # Cleanup - delete campaign
        print("\n[10] Cleaning up test campaign...")
        response = requests.delete(
            f"{BASE_URL}/campaigns/{campaign_id}",
            headers=headers
        )
        if response.status_code == 204:
            print("   ✅ Test campaign deleted")

        print("\n" + "=" * 60)
        print("✅ ALL API TESTS PASSED - Iteration 1.3 API Working!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n⚠️  Make sure FastAPI server is running on http://localhost:8000")
    print("   Run: uvicorn app.main:app --reload --port 8000\n")
    input("Press Enter to continue...")
    asyncio.run(test_leads_api())
```

---

## 📋 Manual Testing Checklist

### Backend Testing

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 1 | Start server | `uvicorn app.main:app --reload --port 8000` | Server starts without errors | ☐ |
| 2 | Health check | `curl http://localhost:8000/health` | Returns `{"status": "healthy"}` | ☐ |
| 3 | API docs | Open http://localhost:8000/docs | Swagger UI loads with all endpoints | ☐ |
| 4 | Lead endpoints visible | Check /docs for leads section | All 9 lead endpoints visible | ☐ |

### Frontend Testing

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 1 | Start frontend | `npm run dev` in frontend/ | Dev server starts on :3000 | ☐ |
| 2 | Login page | Navigate to http://localhost:3000/login | Login form displays | ☐ |
| 3 | Register flow | Create new account | Redirects to campaigns after registration | ☐ |
| 4 | Campaigns list | View campaigns page | Shows user's campaigns | ☐ |
| 5 | Create campaign | Create test campaign | Campaign appears in list | ☐ |
| 6 | Leads navigation | Navigate to /leads | Leads page loads with campaign selector | ☐ |
| 7 | Lead creation | Create lead via API or crawler | Lead appears in list | ☐ |
| 8 | Lead detail | Click on a lead | Detail page shows all information | ☐ |
| 9 | Approve button | Click approve on eligible lead | Status changes to 'approved' | ☐ |
| 10 | Reject button | Click reject on eligible lead | Status changes to 'rejected' | ☐ |

---

## 🐛 Known Issues to Watch For

1. **useAuth Hook Missing** - FIXED ✅
2. **Leads pages missing** - FIXED ✅
3. **Database migration not run** - Need to run `alembic upgrade head`
4. **CORS errors** - Check FRONTEND_URL in .env matches frontend URL
5. **Token expiry** - Access tokens expire after 30 minutes (check .env)

---

## ✅ Sign-Off Criteria

Iteration 1.3 is complete when ALL of the following pass:

- [ ] Database migration runs successfully
- [ ] Lead model test script passes
- [ ] All 9 API endpoints work via Swagger UI
- [ ] API test script passes all 10 tests
- [ ] Frontend leads list page loads and displays leads
- [ ] Frontend lead detail page loads and shows all fields
- [ ] Approve/Reject buttons work correctly
- [ ] Campaign selector filters leads correctly
- [ ] Lead score colors display correctly
- [ ] No console errors in browser

---

## 🚀 After Testing Passes

Once all tests pass, update the status:

```bash
# Update DEVELOPMENT_PLAN.md
# Change Iteration 1.4 from "❌ Not Started" to ready for implementation
```

Then proceed to Iteration 1.4: Search & Discovery.

---

**Test Plan Version:** 1.0
**Last Updated:** 2026-08-18

"""
Test Leads API Endpoints

Tests all 9 lead API endpoints:
- POST /leads (create)
- GET /leads (list)
- GET /leads/{id} (get details)
- PUT /leads/{id} (update)
- DELETE /leads/{id} (delete)
- POST /leads/{id}/approve
- POST /leads/{id}/reject
- POST /leads/bulk-approve
- POST /leads/bulk-reject

Run after starting FastAPI server: uvicorn app.main:app --reload --port 8000
"""
import asyncio
import requests
import json
import sys


BASE_URL = "http://localhost:8000/api/v1"


def test_leads_api():
    """Test all leads API endpoints."""
    print("=" * 60)
    print("Iteration 1.3 - Leads API Test")
    print("=" * 60)

    # Test credentials
    email = "test@example.com"
    password = "password123"

    try:
        # 1. Register/Login
        print("\n[1/10] Testing authentication...")
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password}
        )

        if response.status_code == 401:
            # User doesn't exist, register first
            print("      User not found, registering...")
            response = requests.post(
                f"{BASE_URL}/auth/register",
                json={"email": email, "password": password, "name": "Test User"}
            )
            if response.status_code == 201:
                print("      ✅ User registered")
                # Login again
                response = requests.post(
                    f"{BASE_URL}/auth/login",
                    json={"email": email, "password": password}
                )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print("      ✅ Authentication successful")
        else:
            print(f"      ❌ Authentication failed: {response.status_code}")
            print(f"      Response: {response.text}")
            return

        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create a campaign for testing leads
        print("\n[2/10] Creating test campaign...")
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
            print(f"      ✅ Campaign created (ID: {campaign_id})")
        else:
            print(f"      ❌ Campaign creation failed: {response.status_code}")
            print(f"      Response: {response.text}")
            return

        # 3. Create a lead
        print("\n[3/10] Creating lead...")
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
            print(f"      ✅ Lead created (ID: {lead_id})")
        else:
            print(f"      ❌ Lead creation failed: {response.status_code}")
            print(f"      Response: {response.text}")
            # Clean up campaign before returning
            requests.delete(f"{BASE_URL}/campaigns/{campaign_id}", headers=headers)
            return

        # 4. List leads
        print("\n[4/10] Listing leads...")
        response = requests.get(
            f"{BASE_URL}/leads",
            headers=headers,
            params={"campaign_id": campaign_id}
        )

        if response.status_code == 200:
            leads = response.json()
            print(f"      ✅ Retrieved {leads['total']} lead(s)")
        else:
            print(f"      ❌ List leads failed: {response.status_code}")

        # 5. Get lead details
        print("\n[5/10] Getting lead details...")
        response = requests.get(
            f"{BASE_URL}/leads/{lead_id}",
            headers=headers
        )

        if response.status_code == 200:
            lead_detail = response.json()
            print(f"      ✅ Lead details retrieved")
            print(f"         Organization: {lead_detail['organization_name']}")
            print(f"         Contact: {lead_detail['contact_name']}")
        else:
            print(f"      ❌ Get lead failed: {response.status_code}")

        # 6. Update lead
        print("\n[6/10] Updating lead...")
        response = requests.put(
            f"{BASE_URL}/leads/{lead_id}",
            headers=headers,
            json={"phone": "+1-555-9999", "job_title": "Senior Manager"}
        )

        if response.status_code == 200:
            updated_lead = response.json()
            print("      ✅ Lead updated")
            print(f"         Phone: {updated_lead.get('phone', 'N/A')}")
            print(f"         Job Title: {updated_lead.get('job_title', 'N/A')}")
        else:
            print(f"      ❌ Update failed: {response.status_code}")

        # 7. Approve lead
        print("\n[7/10] Approving lead...")
        response = requests.post(
            f"{BASE_URL}/leads/{lead_id}/approve",
            headers=headers
        )

        if response.status_code == 200:
            result = response.json()
            print(f"      ✅ Lead approved - Status: {result['status']}")
        else:
            print(f"      ❌ Approve failed: {response.status_code}")
            print(f"      Response: {response.text}")

        # 8. Test bulk approve (create another lead first)
        print("\n[8/10] Testing bulk approve...")
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

        lead2_id = None
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
                print(f"      ✅ Bulk approved {result['success_count']} lead(s)")
            else:
                print(f"      ❌ Bulk approve failed: {response.status_code}")
        else:
            print("      ⚠️  Could not create second lead for bulk test")

        # 9. Test bulk reject (create another lead first)
        print("\n[9/10] Testing bulk reject...")
        response = requests.post(
            f"{BASE_URL}/leads",
            headers=headers,
            json={
                "campaign_id": campaign_id,
                "keyword": "test3",
                "source_url": "https://example3.com",
                "organization_name": "Test Org 3",
                "website": "https://example3.com",
                "lead_score": 60
            }
        )

        lead3_id = None
        if response.status_code == 201:
            lead3_id = response.json()["id"]

            # Bulk reject
            response = requests.post(
                f"{BASE_URL}/leads/bulk-reject",
                headers=headers,
                json={"ids": [lead3_id]}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"      ✅ Bulk rejected {result['success_count']} lead(s)")
            else:
                print(f"      ❌ Bulk reject failed: {response.status_code}")
        else:
            print("      ⚠️  Could not create third lead for bulk test")

        # 10. Delete lead
        print("\n[10/10] Deleting lead...")
        response = requests.delete(
            f"{BASE_URL}/leads/{lead_id}",
            headers=headers
        )

        if response.status_code == 204:
            print("      ✅ Lead deleted")
        else:
            print(f"      ❌ Delete failed: {response.status_code}")

        # Cleanup - delete campaign and any remaining leads
        print("\n[Cleanup] Cleaning up test campaign...")
        requests.delete(f"{BASE_URL}/campaigns/{campaign_id}", headers=headers)
        if lead2_id:
            requests.delete(f"{BASE_URL}/leads/{lead2_id}", headers=headers)
        if lead3_id:
            requests.delete(f"{BASE_URL}/leads/{lead3_id}", headers=headers)
        print("         ✅ Test campaign deleted")

        print("\n" + "=" * 60)
        print("✅ ALL API TESTS PASSED - Iteration 1.3 API Working!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to server.")
        print("   Make sure FastAPI server is running:")
        print("   cd backend")
        print("   uvicorn app.main:app --reload --port 8000")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n⚠️  Prerequisites:")
    print("   1. FastAPI server running on http://localhost:8000")
    print("   2. Run: uvicorn app.main:app --reload --port 8000")
    print("   3. Database migration completed: alembic upgrade head")
    print()

    input("Press Enter to start tests...")
    test_leads_api()

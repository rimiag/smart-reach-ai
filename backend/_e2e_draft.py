"""Throwaway draft-editing endpoint test (deleted after running)."""

import asyncio
import sys
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import delete, select


async def setup() -> None:
    from app.db.base import AsyncSessionLocal
    from app.models.campaign import Campaign
    from app.models.lead import Lead
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).limit(1))).scalars().first()
        campaign = Campaign(user_id=user.id, name="DRAFT-edit-test", keywords=["kw"], status="ready")
        db.add(campaign)
        await db.flush()
        db.add(Lead(
            campaign_id=campaign.id,
            user_id=user.id,
            keyword="kw",
            source_url="http://edit.example",
            organization_name="Editable Corp",
            website="https://edit.example",
            email="edit@example.com",
            status="review",
            generated_email="Subject: Old subject\n\nOld body",
        ))
        db.add(Lead(
            campaign_id=campaign.id,
            user_id=user.id,
            keyword="kw",
            source_url="http://sent.example",
            organization_name="Sent Corp",
            website="https://sent.example",
            email="sent@example.com",
            status="sent",
            generated_email="Subject: Old subject\n\nOld body",
        ))
        await db.commit()
        campaign_id = campaign.id
        lead_id = (
            await db.execute(
                select(Lead).where(
                    Lead.campaign_id == campaign_id,
                    Lead.organization_name == "Editable Corp",
                )
            )
        ).scalars().first().id
        sent_lead_id = (
            await db.execute(
                select(Lead).where(
                    Lead.campaign_id == campaign_id,
                    Lead.organization_name == "Sent Corp",
                )
            )
        ).scalars().first().id
        print(campaign_id, lead_id, sent_lead_id)


def endpoint(campaign_id: int, lead_id: int, sent_lead_id: int) -> None:
    from fastapi.testclient import TestClient

    from app.dependencies import get_current_user
    from app.main import app
    from app.schemas.user import UserResponse

    test_user = UserResponse(
        id=1, email="t@example.com", role="user", is_active=True, created_at=datetime.utcnow()
    )
    app.dependency_overrides[get_current_user] = lambda: test_user

    with TestClient(app) as client:
        # happy path: edit the draft
        r = client.put(
            f"/api/v1/leads/{lead_id}/draft",
            json={"subject": "Edited subject", "body": "Edited body with more detail"},
        )
        assert r.status_code == 200, r.text[:300]
        assert r.json()["generated_email"] == "Subject: Edited subject\n\nEdited body with more detail", r.text

        # empty subject -> 400/422
        r = client.put(f"/api/v1/leads/{lead_id}/draft", json={"subject": "  ", "body": "b"})
        assert r.status_code in (400, 422), r.status_code

        # sent lead -> editing not allowed
        r = client.put(f"/api/v1/leads/{sent_lead_id}/draft", json={"subject": "s", "body": "b"})
        assert r.status_code == 400, r.status_code

        # verify/approve endpoint still works after the edit
        r = client.post(f"/api/v1/leads/{lead_id}/approve")
        assert r.status_code == 200, r.text[:200]
        assert r.json()["status"] == "approved"

        # send queue now contains the lead (approved + draft)
        r = client.post(
            f"/api/v1/campaigns/{campaign_id}/send",
            json={"sender_name": "R", "from_email": "x@y.com"},
        )
        # SMTP likely unconfigured here; accept 200 (queued) or 400 (unconfigured)
        assert r.status_code in (200, 400), r.text[:200]

    print("DRAFT ENDPOINT OK")


async def cleanup() -> None:
    from app.db.base import AsyncSessionLocal
    from app.models.campaign import Campaign
    from app.models.lead import Lead

    async with AsyncSessionLocal() as db:
        campaigns = (
            await db.execute(select(Campaign).where(Campaign.name.like("DRAFT-edit-test%")))
        ).scalars().all()
        for campaign in campaigns:
            await db.execute(delete(Lead).where(Lead.campaign_id == campaign.id))
            await db.execute(delete(Campaign).where(Campaign.id == campaign.id))
        await db.commit()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "setup":
        asyncio.run(setup())
    elif mode == "test":
        endpoint(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
    elif mode == "cleanup":
        asyncio.run(cleanup())
    else:
        raise SystemExit("modes: setup | test <cid> <lid> <sent_lid> | cleanup")

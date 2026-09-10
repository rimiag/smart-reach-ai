"""
Email Sending Tasks

Phase 3: sends the approved, drafted leads of a campaign via the email
service. Dispatched by the "Review & Send" flow after explicit human
approval - never automatic.
"""

import asyncio
import logging
from typing import Any, Dict

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.send_tasks.send_campaign_emails", time_limit=7200, soft_time_limit=7100
)
def send_campaign_emails(
    campaign_id: int,
    sender_name: str,
    sender_company: str = "",
    from_email: str = "",
    reply_to: str = "",
) -> Dict[str, Any]:
    """
    Celery task: send approved outreach emails for a campaign.

    Politeness pacing and volume limits live in the email service; a run that
    hits a limit stops and can be resumed by clicking send again.
    """
    from app.services.email_service import email_service

    logger.info("Celery: sending approved emails for campaign %d", campaign_id)
    return asyncio.run(
        email_service.send_campaign(
            campaign_id,
            sender_name=sender_name,
            sender_company=sender_company,
            from_email=from_email,
            reply_to=reply_to,
        )
    )

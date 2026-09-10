"""
Sending Rate Limits

Guardrails for outbound outreach email (Phase 3). A campaign send stops
politely when a limit is reached and can be resumed the next day/hour by
clicking send again - leads are processed in order, so already-sent leads
are never re-sent.
"""

import logging
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_log import EmailLog
from app.models.lead import Lead

logger = logging.getLogger(__name__)


@dataclass
class LimitStatus:
    """Result of a limit check for one user."""

    sent_today: int
    sent_last_hour: int
    daily_limit: int
    hourly_limit: int

    @property
    def can_send(self) -> bool:
        return self.sent_today < self.daily_limit and self.sent_last_hour < self.hourly_limit

    @property
    def reason(self) -> str:
        if self.sent_today >= self.daily_limit:
            return f"daily limit reached ({self.sent_today}/{self.daily_limit})"
        if self.sent_last_hour >= self.hourly_limit:
            return f"hourly limit reached ({self.sent_last_hour}/{self.hourly_limit})"
        return ""


class SendingLimits:
    """Checks outbound email volume against configured guardrails."""

    def __init__(
        self,
        daily_limit: int,
        hourly_limit: int,
        delay_between_sends: int,
        days_between_emails: int,
    ) -> None:
        self.daily_limit = daily_limit
        self.hourly_limit = hourly_limit
        self.delay_between_sends = delay_between_sends
        self.days_between_emails = days_between_emails

    @classmethod
    def from_settings(cls) -> "SendingLimits":
        from app.core.config import settings

        return cls(
            daily_limit=settings.default_daily_email_limit,
            hourly_limit=settings.default_hourly_email_limit,
            delay_between_sends=settings.send_delay_seconds,
            days_between_emails=settings.default_emails_per_lead_days,
        )

    async def current_status(self, db: AsyncSession, user_id: int) -> LimitStatus:
        """Count the user's sent emails today and in the last hour."""
        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        hour_ago = now - timedelta(hours=1)

        sent_today = (
            await db.execute(
                select(func.count(EmailLog.id)).where(
                    EmailLog.user_id == user_id,
                    EmailLog.status == "sent",
                    EmailLog.created_at >= start_of_day,
                )
            )
        ).scalar() or 0

        sent_last_hour = (
            await db.execute(
                select(func.count(EmailLog.id)).where(
                    EmailLog.user_id == user_id,
                    EmailLog.status == "sent",
                    EmailLog.created_at >= hour_ago,
                )
            )
        ).scalar() or 0

        return LimitStatus(
            sent_today=sent_today,
            sent_last_hour=sent_last_hour,
            daily_limit=self.daily_limit,
            hourly_limit=self.hourly_limit,
        )

    async def lead_recently_emailed(self, db: AsyncSession, lead: Lead) -> bool:
        """True when this lead was emailed within the per-lead cooldown window."""
        if not lead.last_emailed_at:
            return False
        cutoff = datetime.utcnow() - timedelta(days=self.days_between_emails)
        return lead.last_emailed_at > cutoff

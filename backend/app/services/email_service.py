"""
Email Service

Phase 3: sends approved, human-reviewed outreach emails with compliance and
safety guardrails:

* suppression list check before every send (unsubscribes/bounces/manual)
* per-lead cooldown (never re-email within N days)
* daily + hourly volume limits - a send run stops politely at the limit
* every attempt is logged to the ``emails`` table (audit trail)
* unsubscribe link + sender identity placeholders are filled at send time
"""

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limits import SendingLimits
from app.integrations.smtp_client import SMTPClient, SMTPSendError
from app.models.campaign import Campaign
from app.models.email_log import EmailLog
from app.models.lead import Lead
from app.models.suppression import Suppression

logger = logging.getLogger(__name__)

UNSUBSCRIBE_FOOTER = (
    "\n\n---\nIf you'd rather not hear from us again, you can unsubscribe here:\n{unsubscribe_url}"
)


class EmailService:
    """Sends approved outreach emails safely."""

    def __init__(
        self,
        smtp_client: Optional[SMTPClient] = None,
        limits: Optional[SendingLimits] = None,
    ) -> None:
        self.smtp = smtp_client or SMTPClient()
        self.limits = limits or SendingLimits.from_settings()

    # ------------------------------------------------------------------
    # Tokens & rendering
    # ------------------------------------------------------------------
    @staticmethod
    def unsubscribe_token(lead: Lead) -> str:
        """Deterministic per-lead token (no storage needed to verify)."""
        from app.core.config import settings

        raw = f"{lead.id}:{(lead.email or '').lower()}:{settings.secret_key}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def unsubscribe_url(self, lead: Lead) -> str:
        from app.core.config import settings

        return f"{settings.api_url}/api/v1/unsubscribe/{lead.id}/{self.unsubscribe_token(lead)}"

    def render_final(
        self,
        lead: Lead,
        generated_email: str,
        sender_name: str,
        sender_company: str,
    ) -> Tuple[str, str]:
        """
        Fill placeholders and append the unsubscribe footer.

        Args:
            lead: Lead with a ``generated_email`` draft
                ("Subject: ...\\n\\n body").
            sender_name / sender_company: Human-approved sender identity.
        Returns:
            (subject, final_body)
        """
        subject_part, _, body = generated_email.partition("\n")
        subject = subject_part.replace("Subject:", "", 1).strip()

        body = body.replace("{{SENDER_NAME}}", sender_name or "{{SENDER_NAME}}")
        body = body.replace("{{SENDER_COMPANY}}", sender_company or sender_name)
        body = body.strip()

        footer = UNSUBSCRIBE_FOOTER.format(unsubscribe_url=self.unsubscribe_url(lead))
        return subject, f"{body}{footer}"

    # ------------------------------------------------------------------
    # Suppression
    # ------------------------------------------------------------------
    async def is_suppressed(
        self, db: AsyncSession, user_id: int, email: str
    ) -> Optional[Suppression]:
        """Return the suppression entry for this email, if any."""
        if not email:
            return None
        result = await db.execute(
            select(Suppression).where(
                Suppression.user_id == user_id,
                Suppression.email == email.strip().lower(),
            )
        )
        return result.scalar_one_or_none()

    async def suppress(
        self,
        db: AsyncSession,
        user_id: int,
        email: str,
        reason: str = "manual",
        lead_id: Optional[int] = None,
    ) -> Suppression:
        """Add an email to the suppression list (idempotent)."""
        email = (email or "").strip().lower()
        existing = await self.is_suppressed(db, user_id, email)
        if existing:
            return existing

        entry = Suppression(user_id=user_id, email=email, reason=reason, lead_id=lead_id)
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        logger.info("Suppressed %s (reason=%s)", email, reason)
        return entry

    async def unsubscribe_by_token(self, db: AsyncSession, lead_id: int, token: str) -> bool:
        """
        Handle an unsubscribe click: verify the token, suppress the email and
        mark the lead. Returns False for invalid tokens/leads.
        """
        lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
        if lead is None or not lead.email:
            return False
        if self.unsubscribe_token(lead) != token:
            return False

        await self.suppress(db, lead.user_id, lead.email, "unsubscribed", lead.id)
        lead.do_not_contact = True
        lead.status = "unsubscribed"
        lead.unsubscribed_at = datetime.utcnow()
        await db.commit()
        return True

    # ------------------------------------------------------------------
    # Campaign sending
    # ------------------------------------------------------------------
    async def send_campaign(
        self,
        campaign_id: int,
        sender_name: str,
        sender_company: str,
        from_email: str,
        reply_to: str = "",
    ) -> Dict[str, Any]:
        """
        Send the approved, drafted leads of a campaign.

        Leads are processed in score order (highest first). The run stops
        politely when volume limits are reached and can be resumed later.

        Raises:
            ValueError: If the campaign does not exist.
            SMTPSendError: If SMTP is not configured.
        """
        from app.db.base import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            campaign = (
                await db.execute(select(Campaign).where(Campaign.id == campaign_id))
            ).scalar_one_or_none()
            if campaign is None:
                raise ValueError(f"Campaign {campaign_id} not found")

            if not self.smtp.is_configured:
                raise SMTPSendError(
                    "SMTP is not configured - set SMTP_HOST, SMTP_USER and "
                    "SMTP_PASSWORD (and optionally SMTP_FROM_EMAIL)"
                )

            leads = (
                (
                    await db.execute(
                        select(Lead)
                        .where(Lead.campaign_id == campaign_id)
                        .where(Lead.status == "approved")
                        .where(Lead.generated_email.is_not(None))
                        .order_by(Lead.lead_score.desc(), Lead.id)
                    )
                )
                .scalars()
                .all()
            )

            summary: Dict[str, Any] = {
                "campaign_id": campaign_id,
                "leads_ready": len(leads),
                "sent": 0,
                "failed": 0,
                "skipped_suppressed": 0,
                "skipped_recently_emailed": 0,
                "stopped_reason": "",
            }

            if not leads:
                logger.info("Send for campaign %d: no approved leads with drafts", campaign_id)
                return summary

            limit_status = await self.limits.current_status(db, campaign.user_id)
            user_id = campaign.user_id

            for index, lead in enumerate(leads):
                # Volume limits - stop the run politely, resumable later.
                limit_status = await self.limits.current_status(db, user_id)
                if not limit_status.can_send:
                    summary["stopped_reason"] = limit_status.reason
                    logger.warning(
                        "Send run for campaign %d stopped: %s (%d leads remaining)",
                        campaign_id,
                        limit_status.reason,
                        len(leads) - index,
                    )
                    break

                if not lead.email:
                    summary["failed"] += 1
                    continue

                suppression = await self.is_suppressed(db, user_id, lead.email)
                if suppression is not None:
                    summary["skipped_suppressed"] += 1
                    continue

                if await self.limits.lead_recently_emailed(db, lead):
                    summary["skipped_recently_emailed"] += 1
                    continue

                subject, body = self.render_final(
                    lead, lead.generated_email or "", sender_name, sender_company
                )

                try:
                    sent = await self.smtp.send(
                        from_addr=from_email,
                        from_name=sender_name,
                        to_addr=lead.email,
                        subject=subject,
                        body=body,
                        reply_to=reply_to or from_email,
                    )
                except SMTPSendError as exc:
                    logger.error("Send failed for lead %d: %s", lead.id, exc)
                    db.add(
                        EmailLog(
                            campaign_id=campaign_id,
                            lead_id=lead.id,
                            user_id=user_id,
                            to_email=lead.email,
                            from_email=from_email,
                            subject=subject,
                            body=body,
                            status="failed",
                            provider="smtp",
                            error_message=str(exc)[:500],
                            unsubscribe_token=self.unsubscribe_token(lead),
                        )
                    )
                    lead.status = "approved"  # stay approved for the next run
                    summary["failed"] += 1
                    await db.commit()
                    continue

                db.add(
                    EmailLog(
                        campaign_id=campaign_id,
                        lead_id=lead.id,
                        user_id=user_id,
                        to_email=lead.email,
                        from_email=from_email,
                        subject=subject,
                        body=body,
                        status="sent",
                        provider="smtp",
                        message_id=sent.message_id,
                        unsubscribe_token=self.unsubscribe_token(lead),
                        sent_at=datetime.utcnow(),
                    )
                )
                lead.status = "sent"
                lead.emails_sent = (lead.emails_sent or 0) + 1
                lead.last_emailed_at = datetime.utcnow()
                summary["sent"] += 1
                await db.commit()

                # Polite pacing between sends (skip the sleep after the last).
                if index < len(leads) - 1:
                    await asyncio.sleep(self.limits.delay_between_sends)

            logger.info("Send run complete for campaign %d: %s", campaign_id, summary)
            return summary


email_service = EmailService()

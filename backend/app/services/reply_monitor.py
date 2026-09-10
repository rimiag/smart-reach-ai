"""
Reply Monitor

Phase 4: detects inbound replies to outreach emails, classifies them with AI
and drives lead status updates.

Matching strategy (per fetched message):
1. Message-ID headers (In-Reply-To / References) matched against our stored
   outreach emails' ``message_id`` - precise.
2. Fallback: sender address matched to a lead's email (most recent lead).
3. No match -> the message is ignored (e.g. unrelated mail in the mailbox).

Duplicates are prevented via the unique ``in_reply_to`` column and a
lead-level guard (one reply per Message-ID; unread counting by category).
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.reply_agent import ReplyClassificationAgent
from app.db.base import AsyncSessionLocal
from app.integrations.imap_client import ImapClient, ImapError, RawReply
from app.models.email_log import EmailLog
from app.models.lead import Lead
from app.models.reply import Reply
from app.services.email_service import email_service

logger = logging.getLogger(__name__)

# Lead status per reply category (categories not listed keep status 'replied')
CATEGORY_STATUS_MAP = {
    "interested": "interested",
    "request_meeting": "interested",
    "pricing_request": "interested",
    "need_more_info": "interested",
    "not_interested": "not_interested",
    "unsubscribe": "unsubscribed",
    "out_of_office": "replied",
    "wrong_contact": "replied",
    "other": "replied",
}


class ReplyMonitor:
    """Detects, classifies and stores replies to outreach emails."""

    # Lookback window for the first-ever check (no stored replies yet).
    INITIAL_LOOKBACK_DAYS = 3

    def __init__(
        self,
        imap_client: Optional[ImapClient] = None,
        classifier: Optional[ReplyClassificationAgent] = None,
    ) -> None:
        self.imap = imap_client or ImapClient(
            _settings().imap_host,
            _settings().imap_port,
            _settings().imap_user,
            _settings().imap_password,
            _settings().imap_folder,
        )
        self.classifier = classifier

    # ------------------------------------------------------------------
    # Fetch (sync - imaplib is blocking)
    # ------------------------------------------------------------------
    def fetch_raw_replies(self, since: datetime) -> List[RawReply]:
        """Fetch unread mailbox messages received after ``since`` (UTC)."""
        return self.imap.fetch_since(since)

    async def high_water_mark(self) -> datetime:
        """The created_at of the latest stored reply, or an initial lookback."""
        async with AsyncSessionLocal() as db:
            latest = (await db.execute(select(func.max(Reply.created_at)))).scalar()
        if latest is not None:
            return latest
        return datetime.utcnow() - timedelta(days=self.INITIAL_LOOKBACK_DAYS)

    # ------------------------------------------------------------------
    # Ingest (async - DB + AI)
    # ------------------------------------------------------------------
    async def ingest_replies(self, replies: List[RawReply]) -> Dict[str, Any]:
        """
        Match, classify and store raw replies.

        Returns a summary dict: matched / unmatched / duplicates / by-category.
        """
        summary: Dict[str, Any] = {
            "fetched": len(replies),
            "matched": 0,
            "unmatched": 0,
            "duplicates": 0,
            "by_category": {},
            "failed": 0,
        }
        if not replies:
            return summary

        classifier = self.classifier or ReplyClassificationAgent()

        async with AsyncSessionLocal() as db:
            for raw in replies:
                try:
                    match = await self._match_reply(raw)
                    if match is None:
                        summary["unmatched"] += 1
                        logger.info(
                            "Reply from %s does not match any known lead - ignored",
                            raw.from_email,
                        )
                        continue

                    lead_id, campaign_id, user_id, in_reply_to = match

                    # Duplicate guard: same thread reference already ingested
                    if in_reply_to:
                        existing = (
                            await db.execute(select(Reply).where(Reply.in_reply_to == in_reply_to))
                        ).scalar_one_or_none()
                        if existing is not None:
                            summary["duplicates"] += 1
                            continue

                    classification = await classifier.classify(
                        from_email=raw.from_email, subject=raw.subject or "", body=raw.body
                    )

                    lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one()

                    db.add(
                        Reply(
                            campaign_id=campaign_id,
                            lead_id=lead.id,
                            user_id=user_id,
                            from_email=raw.from_email,
                            from_name=raw.from_name or None,
                            subject=(raw.subject or "")[:255],
                            body=raw.body,
                            category=classification.category,
                            ai_summary=classification.summary or None,
                            classification_error=(
                                None if classification.used_ai else "classified without AI"
                            ),
                            in_reply_to=in_reply_to or None,
                            received_at=raw.received_at,
                        )
                    )

                    self._apply_status(lead, classification.category)
                    summary["matched"] += 1
                    summary["by_category"][classification.category] = (
                        summary["by_category"].get(classification.category, 0) + 1
                    )
                    await db.commit()

                except Exception as exc:
                    logger.exception("Failed to ingest reply from %s", raw.from_email)
                    summary["failed"] += 1
                    await db.rollback()

        logger.info("Reply ingest: %s", summary)
        return summary

    async def _match_reply(self, raw: RawReply) -> Optional[tuple]:
        """
        Match a raw reply to (lead_id, campaign_id, user_id, in_reply_to).

        Returns None when the sender is unknown. Ids only - the caller loads
        the lead in its own session for update. When several records match
        (a lead can exist in multiple campaigns), the most recent one wins.
        """
        async with AsyncSessionLocal() as db:
            # 1. Thread match: In-Reply-To references our stored Message-ID
            if raw.in_reply_to:
                email_log = (
                    (
                        await db.execute(
                            select(EmailLog)
                            .where(EmailLog.message_id == raw.in_reply_to)
                            .order_by(EmailLog.id.desc())
                        )
                    )
                    .scalars()
                    .first()
                )
                if email_log is not None:
                    return (
                        email_log.lead_id,
                        email_log.campaign_id,
                        email_log.user_id,
                        raw.in_reply_to,
                    )

            # 2. Sender match: the reply's From address equals a lead's email
            lead = (
                (
                    await db.execute(
                        select(Lead).where(Lead.email == raw.from_email).order_by(Lead.id.desc())
                    )
                )
                .scalars()
                .first()
            )
            if lead is not None:
                return lead.id, lead.campaign_id, lead.user_id, raw.in_reply_to or None

            return None

    @staticmethod
    def _apply_status(lead: Lead, category: str) -> None:
        """Update the lead's status from the reply category."""
        lead.status = CATEGORY_STATUS_MAP.get(category, "replied")
        if category == "unsubscribe":
            lead.do_not_contact = True
            lead.unsubscribed_at = datetime.utcnow()


def _settings():
    from app.core.config import settings

    return settings


# -----------------------------------------------------------------------------
# Sync convenience wrapper used by Celery tasks and manual triggers
# -----------------------------------------------------------------------------
async def run_reply_check_async() -> Dict[str, Any]:
    """Fetch new mailbox replies and ingest them."""
    monitor = ReplyMonitor()
    if not monitor.imap.is_configured:
        return {"skipped": "IMAP is not configured - set IMAP_HOST, IMAP_USER and IMAP_PASSWORD"}

    since = await monitor.high_water_mark()
    # imaplib is blocking: run the fetch in a worker thread.
    replies = await asyncio.to_thread(monitor.fetch_raw_replies, since)
    return await monitor.ingest_replies(replies)

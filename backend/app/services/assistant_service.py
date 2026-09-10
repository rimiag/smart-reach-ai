"""
AI Sales Assistant

Phase 5: answers natural-language questions about the user's campaigns,
leads and replies - grounded strictly in their own database content.
"""

import logging
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.ai_base import LLMClient, get_ai_client
from app.models.campaign import Campaign
from app.models.email_log import EmailLog
from app.models.lead import Lead
from app.models.reply import Reply
from app.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the analytics assistant for a B2B lead generation \
platform. Answer the user's question using ONLY the CONTEXT data below - \
never invent numbers, names, or facts.

Rules:
- Be concise and concrete; quote exact counts and names from the context
- If the context doesn't contain the answer, say so plainly
- The user's leads, campaigns, and replies below belong to them; refer to \
campaigns by name
- Reply in the language of the question"""

MAX_CONTEXT_LEADS = 15
MAX_CONTEXT_REPLIES = 10
LEAD_FIELDS_LIMIT = 200  # chars per lead reasoning snippet


class AssistantService:
    """Answers natural-language questions grounded in user data."""

    def __init__(self, client: LLMClient = None) -> None:
        self.client = client or get_ai_client()

    async def answer(self, db: AsyncSession, user_id: int, question: str) -> Dict[str, Any]:
        """
        Answer a question using the user's data as context.

        Raises:
            AIProviderError: If no AI provider is configured.
        """
        context = await self._build_context(db, user_id)
        response = await self.client.complete(
            system=SYSTEM_PROMPT,
            user=f"CONTEXT:\n{context}\n\nQUESTION: {question}",
            max_tokens=1024,
            temperature=0.3,
        )
        return {"answer": response.text.strip(), "model": response.model}

    async def _build_context(self, db: AsyncSession, user_id: int) -> str:
        """Assemble a compact, factual context bundle for the prompt."""
        sections: list = []

        # Volume metrics
        reply_analytics = await analytics_service.get_reply_analytics(db, user_id)
        sections.append(
            "VOLUME:\n"
            f"- Emails sent: {reply_analytics['emails_sent']}\n"
            f"- Total replies: {reply_analytics['total_replies']}\n"
            f"- Unread replies: {reply_analytics['unread_replies']}\n"
            f"- Replies last 7 days: {reply_analytics['replies_last_7_days']}\n"
            f"- Reply rate: {reply_analytics['reply_rate_percent']}%"
        )
        if reply_analytics.get("by_category"):
            cats = ", ".join(f"{k}: {v}" for k, v in reply_analytics["by_category"].items())
            sections.append(f"- Replies by category: {cats}")

        # Campaigns
        campaigns = (
            (
                await db.execute(
                    select(Campaign)
                    .where(Campaign.user_id == user_id)
                    .order_by(Campaign.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        if campaigns:
            lines = [
                f"- {c.name} (status: {c.status}, keywords: {', '.join(c.keywords or [])})"
                for c in campaigns
            ]
            sections.append("CAMPAIGNS:\n" + "\n".join(lines))

        # Top leads by score
        leads = (
            (
                await db.execute(
                    select(Lead)
                    .where(Lead.user_id == user_id)
                    .order_by(Lead.lead_score.desc(), Lead.id.desc())
                    .limit(MAX_CONTEXT_LEADS)
                )
            )
            .scalars()
            .all()
        )
        if leads:
            lines = [
                f"- {lead.organization_name} (status: {lead.status}, score: {lead.lead_score}, "
                f"email: {lead.email or 'none'}, campaign: {lead.campaign_id}"
                + (
                    f", notes: {(lead.ai_reasoning or '')[:LEAD_FIELDS_LIMIT]}"
                    if lead.ai_reasoning
                    else ""
                )
                + ")"
                for lead in leads
            ]
            sections.append(f"TOP {len(leads)} LEADS BY SCORE:\n" + "\n".join(lines))

        # Recent replies
        replies = (
            (
                await db.execute(
                    select(Reply)
                    .where(Reply.user_id == user_id)
                    .order_by(Reply.created_at.desc())
                    .limit(MAX_CONTEXT_REPLIES)
                )
            )
            .scalars()
            .all()
        )
        if replies:
            lines = [
                f"- From {reply.from_email} (category: {reply.category}): "
                f"{(reply.ai_summary or reply.subject or reply.body)[:150]}"
                for reply in replies
            ]
            sections.append("RECENT REPLIES:\n" + "\n".join(lines))

        return "\n\n".join(sections)


assistant_service = AssistantService()

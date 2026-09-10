"""
Reply Detection Tasks

Phase 4: periodic mailbox polling for inbound replies (Celery beat) plus
manual triggering. IMAP polling is blocking and runs in a worker thread; DB
+ AI work is async.
"""

import asyncio
import logging
from typing import Any, Dict

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.reply_tasks.check_replies", time_limit=1800, soft_time_limit=1700)
def check_replies() -> Dict[str, Any]:
    """Celery task (beat): poll the mailbox and ingest new replies."""
    from app.services.reply_monitor import run_reply_check_async

    logger.info("Celery: checking mailbox for replies")
    summary = asyncio.run(run_reply_check_async())
    logger.info("Reply check complete: %s", summary)
    return summary

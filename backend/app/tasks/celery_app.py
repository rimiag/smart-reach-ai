"""
Celery Application Configuration

Configures Celery for background task processing with Redis as broker.
"""

from celery import Celery

from app.core.config import settings

# -----------------------------------------------------------------------------
# Create Celery App
# -----------------------------------------------------------------------------
celery_app = Celery(
    "ai_lead_generation",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# -----------------------------------------------------------------------------
# Celery Configuration
# -----------------------------------------------------------------------------
celery_app.conf.update(
    # Task settings
    task_track_started=settings.celery_task_tracked,
    task_time_limit=settings.celery_task_time_limit,
    worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
    worker_max_tasks_per_child=settings.celery_worker_max_tasks_per_child,
    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Routing
    task_routes={
        "app.tasks.search_tasks.*": {"queue": "search"},
        "app.tasks.crawl_tasks.*": {"queue": "crawl"},
        "app.tasks.qualify_tasks.*": {"queue": "ai"},
        "app.tasks.followup_tasks.*": {"queue": "ai"},
        "app.tasks.email_tasks.send_email": {"queue": "email"},
    },
)

# -----------------------------------------------------------------------------
# Task Registration
# -----------------------------------------------------------------------------
# Import every task module explicitly so their @task decorators register with
# this app in the worker process (autodiscovery does not reliably import these
# modules since the package does not follow the <pkg>.tasks layout).
from app.tasks import crawl_tasks  # noqa: E402, F401
from app.tasks import email_tasks  # noqa: E402, F401
from app.tasks import followup_tasks  # noqa: E402, F401
from app.tasks import qualify_tasks  # noqa: E402, F401
from app.tasks import reply_tasks  # noqa: E402, F401
from app.tasks import search_tasks  # noqa: E402, F401
from app.tasks import send_tasks  # noqa: E402, F401

celery_app.autodiscover_tasks(["app.tasks"])

# -----------------------------------------------------------------------------
# Periodic Tasks (Celery beat) - reply detection + follow-up sweeps
# -----------------------------------------------------------------------------
beat_schedule: dict = {}
if settings.reply_check_enabled:
    beat_schedule["check-replies-periodically"] = {
        "task": "app.tasks.reply_tasks.check_replies",
        "schedule": float(settings.reply_check_interval_minutes * 60),
    }
if settings.follow_up_enabled:
    beat_schedule["followup-sweep-daily"] = {
        "task": "app.tasks.followup_tasks.followup_sweep",
        "schedule": 86400.0,  # once a day
    }
celery_app.conf.beat_schedule = beat_schedule


# -----------------------------------------------------------------------------
# Health Check Task
# -----------------------------------------------------------------------------
@celery_app.task
def health_check() -> str:
    """Simple health check task."""
    return "Celery worker is healthy"

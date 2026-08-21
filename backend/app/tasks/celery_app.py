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
        "app.tasks.email_tasks.send_email": {"queue": "email"},
    },
)

# -----------------------------------------------------------------------------
# Task Auto-discovery
# -----------------------------------------------------------------------------
celery_app.autodiscover_tasks(["app.tasks"])


# -----------------------------------------------------------------------------
# Health Check Task
# -----------------------------------------------------------------------------
@celery_app.task
def health_check() -> str:
    """Simple health check task."""
    return "Celery worker is healthy"

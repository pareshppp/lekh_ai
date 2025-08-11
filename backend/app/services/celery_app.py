from celery import Celery
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create Celery application
celery_app = Celery(
    "lekh-agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.services.story_runner"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # Retry configuration
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result configuration
    result_expires=3600,  # 1 hour
    # Route tasks
    task_routes={
        "app.services.story_runner.run_story_generation_task": {"queue": "story_generation"},
    },
)

logger.info("Celery app configured")

if __name__ == "__main__":
    celery_app.start()
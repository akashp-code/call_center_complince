from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "call_center_compliance",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,                     # Re-queue if worker crashes
    worker_prefetch_multiplier=1,            # One task per worker at a time (STT is heavy)
    task_soft_time_limit=180,               # 3 min soft limit
    task_time_limit=240,                    # 4 min hard limit
    result_expires=600,                     # Results expire after 10 min
)

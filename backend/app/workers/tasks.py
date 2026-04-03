from app.workers.celery_app import celery_app
from app.services.pipeline import run_pipeline
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.process_call",
    max_retries=0,   # pipeline handles its own fallback — no retry needed
)
def process_call_task(self, audio_base64: str, language: str) -> dict:
    """
    Celery task: runs the full AI pipeline for one call recording.

    pipeline.run_pipeline() is fault-tolerant and always returns a valid dict
    (including a safe fallback on failure), so this task never raises.
    """
    logger.info("task_started", task_id=self.request.id, language=language)
    result = run_pipeline(audio_base64=audio_base64, language=language)
    logger.info(
        "task_completed",
        task_id=self.request.id,
        status=result.get("status"),
        processing_time=result.get("processingTime"),
    )
    return result


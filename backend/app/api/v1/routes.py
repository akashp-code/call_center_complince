"""
API routes for call analytics.
This version runs the pipeline DIRECTLY (no Celery/Redis required).
Easier for local dev and free deployment on Render.
"""

import asyncio
import time
from fastapi import APIRouter, Depends, HTTPException

from app.core.security import validate_api_key
from app.core.logging import get_logger
from app.schemas.request import CallAnalyticsRequest
from app.schemas.response import CallAnalyticsResponse, ErrorResponse
from app.services.pipeline import run_pipeline

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/call-analytics",
    response_model=CallAnalyticsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="Analyze a call center recording for compliance",
)
async def analyze_call(
    body: CallAnalyticsRequest,
    _: str = Depends(validate_api_key),
):
    request_start = time.perf_counter()
    language = body.language.value
    logger.info("request_received", language=language, audio_len=len(body.audioBase64))

    try:
        # Run CPU-bound pipeline in a thread pool so it doesn't block the event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            run_pipeline,
            body.audioBase64,
            language,
        )

        elapsed = round(time.perf_counter() - request_start, 2)
        logger.info("request_complete", elapsed_seconds=elapsed)
        return result

    except Exception as e:
        elapsed = round(time.perf_counter() - request_start, 2)
        logger.error("request_failed", error=str(e), elapsed_seconds=elapsed)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@router.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}

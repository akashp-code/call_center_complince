import asyncio
import os
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import validate_api_key
from app.core.logging import get_logger
from app.schemas.request import CallAnalyticsRequest
from app.schemas.response import CallIntelligenceResponse
from app.services.pipeline import run_pipeline

router = APIRouter()
logger = get_logger(__name__)


@router.post("/analyze", response_model=CallIntelligenceResponse)
async def analyze_call(body: CallAnalyticsRequest, _: str = Depends(validate_api_key)):
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, run_pipeline, body.audioBase64, body.language, body.audioFormat,
        )
        return result
    except Exception as e:
        logger.error("pipeline_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "AI Conversation Intelligence Platform"}


@router.get("/debug-env", include_in_schema=False)
async def debug_env():
    from app.core.config import get_settings

    settings = get_settings()

    return {
        "GROQ_API_KEY": f"{'SET' if len(settings.GROQ_API_KEY) > 10 else 'MISSING'} (length={len(settings.GROQ_API_KEY)})",
        "OPENAI_API_KEY": f"{'SET' if len(settings.OPENAI_API_KEY) > 10 else 'MISSING'} (length={len(settings.OPENAI_API_KEY)})",
    }
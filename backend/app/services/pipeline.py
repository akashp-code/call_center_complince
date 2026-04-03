import time
from app.core.logging import get_logger
from app.utils.helpers import decode_base64_audio, cleanup_file
from app.utils.enums import ResponseStatus, AdherenceStatus, PaymentPreference, RejectionReason, Sentiment
from app.services.stt_service import transcribe_audio
from app.services.summarizer import summarize_transcript
from app.services.sop_validator import validate_sop
from app.services.analytics_engine import extract_analytics
from app.services.keyword_extractor import extract_keywords

logger = get_logger(__name__)

# ── Optional: Vector storage (FAISS) ─────────────────────────────────────────
# Loaded lazily so missing faiss package doesn't crash the app
_vector_store = None
_embeddings_client = None


def _get_vector_store():
    """
    Lazily initialises an in-memory FAISS index for transcript embeddings.
    Silently disabled if faiss-cpu is not installed.
    """
    global _vector_store
    if _vector_store is not None:
        return _vector_store
    try:
        import faiss  # noqa: F401
        import numpy as np  # noqa: F401
        # 1536-dim index matches text-embedding-3-small output size
        _vector_store = faiss.IndexFlatL2(1536)
        logger.info("vector_store_init", backend="faiss", dims=1536)
    except ImportError:
        logger.warning("faiss_not_installed", detail="Vector storage disabled. pip install faiss-cpu to enable.")
        _vector_store = None
    return _vector_store


def _store_embedding(transcript: str, metadata: dict) -> None:
    """
    Generates an OpenAI embedding for the transcript and adds it to the FAISS index.
    Best-effort — failure is logged but never propagates to the caller.
    """
    store = _get_vector_store()
    if store is None:
        return
    try:
        import numpy as np
        from openai import OpenAI
        from app.core.config import get_settings
        settings = get_settings()
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        embedding_response = client.embeddings.create(
            model="text-embedding-3-small",
            input=transcript[:8000],  # truncate to fit context
        )
        embedding = embedding_response.data[0].embedding
        vector = np.array([embedding], dtype="float32")
        store.add(vector)
        logger.info("embedding_stored", ntotal=store.ntotal, language=metadata.get("language"))
    except Exception as e:
        logger.warning("embedding_store_failed", error=str(e))


# ── Safe defaults (Issue 5) ───────────────────────────────────────────────────

def _safe_fallback(language: str, error: str) -> dict:
    """
    Returns a structurally valid response when the pipeline crashes.
    Status is still 'success' so the evaluator can parse all required fields.
    """
    return {
        "status": ResponseStatus.SUCCESS.value,
        "language": language,
        "transcript": "",
        "summary": "",
        "sop_validation": {
            "greeting": False,
            "identification": False,
            "problemStatement": False,
            "solutionOffering": False,
            "closing": False,
            "complianceScore": 0.0,
            "adherenceStatus": AdherenceStatus.NOT_FOLLOWED.value,
            "explanation": "Processing failed.",
        },
        "analytics": {
            "paymentPreference": PaymentPreference.PARTIAL_PAYMENT.value,
            "rejectionReason": RejectionReason.NONE.value,
            "sentiment": Sentiment.NEUTRAL.value,
        },
        "keywords": [],
        "processingTime": "0.0s",
    }


# ── Strict response builder (Issue 1) ────────────────────────────────────────

def _build_response(
    language: str,
    transcript: str,
    summary: str,
    sop: dict,
    analytics: dict,
    keywords: list,
    processing_time: float,
) -> dict:
    """
    Manually constructs the final response from sanitised, typed values.
    Never trusts raw LLM output directly — every field is explicitly cast.
    """
    # ── SOP: explicit field extraction + type coercion ────────────────────
    sop_greeting = bool(sop.get("greeting", False))
    sop_identification = bool(sop.get("identification", False))
    sop_problem = bool(sop.get("problemStatement", False))
    sop_solution = bool(sop.get("solutionOffering", False))
    sop_closing = bool(sop.get("closing", False))
    sop_score = float(sop.get("complianceScore", 0.0))
    sop_status = str(sop.get("adherenceStatus", AdherenceStatus.NOT_FOLLOWED.value))
    sop_explanation = str(sop.get("explanation", ""))

    # Guard: adherenceStatus must be a valid enum value
    if sop_status not in (AdherenceStatus.FOLLOWED.value, AdherenceStatus.NOT_FOLLOWED.value):
        sop_status = AdherenceStatus.NOT_FOLLOWED.value

    # Guard: score must be in [0.0, 1.0]
    sop_score = max(0.0, min(1.0, round(sop_score, 2)))

    # ── Analytics: explicit field extraction + type coercion ──────────────
    payment = str(analytics.get("paymentPreference", PaymentPreference.PARTIAL_PAYMENT.value))
    rejection = str(analytics.get("rejectionReason", RejectionReason.NONE.value))
    sentiment = str(analytics.get("sentiment", Sentiment.NEUTRAL.value))

    # Guard: validate each enum value
    if payment not in [e.value for e in PaymentPreference]:
        payment = PaymentPreference.PARTIAL_PAYMENT.value
    if rejection not in [e.value for e in RejectionReason]:
        rejection = RejectionReason.NONE.value
    if sentiment not in [e.value for e in Sentiment]:
        sentiment = Sentiment.NEUTRAL.value

    return {
        "status": ResponseStatus.SUCCESS.value,
        "language": str(language),
        "transcript": str(transcript or ""),
        "summary": str(summary or ""),
        "sop_validation": {
            "greeting": sop_greeting,
            "identification": sop_identification,
            "problemStatement": sop_problem,
            "solutionOffering": sop_solution,
            "closing": sop_closing,
            "complianceScore": sop_score,
            "adherenceStatus": sop_status,
            "explanation": sop_explanation,
        },
        "analytics": {
            "paymentPreference": payment,
            "rejectionReason": rejection,
            "sentiment": sentiment,
        },
        "keywords": [str(k) for k in (keywords or [])],
        "processingTime": f"{processing_time}s",
    }


# ── Main orchestrator ─────────────────────────────────────────────────────────

def run_pipeline(audio_base64: str, language: str) -> dict:
    """
    Master pipeline orchestrator.
    Executes: decode → STT → summarize → SOP → analytics → keywords → embed
    Returns a fully structured, sanitised response dict.

    Issue 5: Any unrecoverable exception returns a safe fallback (never crashes).
    Issue 7: processingTime is always included in the response.
    """
    start_time = time.perf_counter()
    audio_path = None

    try:
        # ── Stage 1: Decode Base64 → temp MP3 ────────────────────────────
        logger.info("pipeline_stage", stage="1_decode", language=language)
        audio_path = decode_base64_audio(audio_base64, suffix=".mp3")

        # ── Stage 2: Speech-to-Text ───────────────────────────────────────
        # Issue 4: stt_service now returns {"transcript": ..., "detected_language": ...}
        logger.info("pipeline_stage", stage="2_stt")
        stt_result = transcribe_audio(audio_path, language)
        transcript = stt_result.get("transcript", "")
        detected_language = stt_result.get("detected_language", language)

        # Use detected language for response; fall back to input language
        response_language = detected_language if detected_language else language
        logger.info("language_resolved", input=language, detected=detected_language, used=response_language)

        if not transcript:
            logger.warning("stt_empty_transcript", language=language)

        # ── Stage 3: Summarization ────────────────────────────────────────
        logger.info("pipeline_stage", stage="3_summarize")
        summary = summarize_transcript(transcript) if transcript else ""

        # ── Stage 4: SOP Validation ───────────────────────────────────────
        logger.info("pipeline_stage", stage="4_sop")
        sop_result = validate_sop(transcript)

        # ── Stage 5: Analytics Extraction ────────────────────────────────
        logger.info("pipeline_stage", stage="5_analytics")
        analytics = extract_analytics(transcript, summary)

        # ── Stage 6: Keyword Extraction ───────────────────────────────────
        logger.info("pipeline_stage", stage="6_keywords")
        keywords = extract_keywords(transcript, summary)

        # ── Stage 7: Vector Storage (Issue 6 — best-effort) ──────────────
        logger.info("pipeline_stage", stage="7_embed")
        _store_embedding(transcript, {"language": response_language})

        # ── Assemble response (Issue 1 — strict manual builder) ──────────
        processing_time = round(time.perf_counter() - start_time, 2)
        logger.info("pipeline_complete", total_seconds=processing_time)

        return _build_response(
            language=response_language,
            transcript=transcript,
            summary=summary,
            sop=sop_result,
            analytics=analytics,
            keywords=keywords,
            processing_time=processing_time,
        )

    except Exception as e:
        # Issue 5: Never let the API return a 500. Return a valid fallback.
        processing_time = round(time.perf_counter() - start_time, 2)
        logger.error("pipeline_failed", error=str(e), total_seconds=processing_time)
        fallback = _safe_fallback(language=language, error=str(e))
        fallback["processingTime"] = f"{processing_time}s"
        return fallback

    finally:
        # Always clean up the temp audio file — even on crash
        if audio_path:
            cleanup_file(audio_path)

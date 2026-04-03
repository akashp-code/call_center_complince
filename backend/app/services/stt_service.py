import whisper
import os
from app.core.logging import get_logger
from app.utils.helpers import timer

logger = get_logger(__name__)

# Load model once at module level (reuse across requests)
_model = None


def _get_model():
    global _model
    if _model is None:
        logger.info("loading_whisper_model", model="base")
        _model = whisper.load_model("base")
    return _model


# Language hint mapping for Whisper
LANGUAGE_HINT_MAP = {
    "Tamil": "ta",
    "Hindi": "hi",
}


@timer("speech_to_text")
def transcribe_audio(audio_path: str, language: str) -> dict:
    """
    Transcribes MP3 audio using OpenAI Whisper.
    Supports Hinglish and Tanglish via language hints.

    Args:
        audio_path: Path to the temporary MP3 file.
        language: "Tamil" or "Hindi" (used as hint; Whisper auto-detects actual language)

    Returns:
        dict with keys:
            "transcript"        — full text of the call
            "detected_language" — language code Whisper identified (e.g. "ta", "hi")
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = _get_model()
    lang_code = LANGUAGE_HINT_MAP.get(language, None)

    logger.info("transcription_start", language=language, lang_code=lang_code)

    result = model.transcribe(
        audio_path,
        language=lang_code,
        task="transcribe",
        fp16=False,                      # CPU compatibility
        verbose=False,
        word_timestamps=False,
        condition_on_previous_text=True,
        temperature=0.0,                 # Deterministic output
    )

    transcript = result.get("text", "").strip()
    # Whisper stores the detected ISO language code in result["language"]
    detected_language = result.get("language", lang_code or language)

    logger.info(
        "transcription_done",
        chars=len(transcript),
        detected_language=detected_language,
    )
    return {"transcript": transcript, "detected_language": detected_language}

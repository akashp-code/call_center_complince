import base64
import functools
import os
import tempfile
import time
from app.core.logging import get_logger

logger = get_logger(__name__)


def decode_base64_audio(audio_base64: str, suffix: str = ".mp3") -> str:
    """
    Decodes a Base64 string and writes it to a temporary file.
    Returns the path to the temp file.
    Caller is responsible for cleanup via cleanup_file().
    """
    try:
        audio_bytes = base64.b64decode(audio_base64)
    except Exception as e:
        raise ValueError(f"Invalid Base64 audio data: {e}")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(audio_bytes)
        tmp.flush()
        tmp_path = tmp.name
    finally:
        tmp.close()

    logger.info("audio_decoded", path=tmp_path, size_bytes=len(audio_bytes))
    return tmp_path


def cleanup_file(path: str) -> None:
    """Safely deletes a file. Logs warning on failure, never raises."""
    try:
        if path and os.path.exists(path):
            os.unlink(path)
            logger.info("temp_file_deleted", path=path)
    except Exception as e:
        logger.warning("temp_file_delete_failed", path=path, error=str(e))


def timer(stage_name: str):
    """
    Decorator that logs execution time of a function.
    Usage: @timer("stt_transcription")
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = round(time.perf_counter() - t0, 3)
                logger.info("stage_timing", stage=stage_name, elapsed_seconds=elapsed)
                return result
            except Exception as e:
                elapsed = round(time.perf_counter() - t0, 3)
                logger.error("stage_failed", stage=stage_name, elapsed_seconds=elapsed, error=str(e))
                raise
        return wrapper
    return decorator

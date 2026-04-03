from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API Auth
    API_KEY: str = "sk_track3_987654321"

    # OpenAI (for LLM tasks + Whisper fallback)
    OPENAI_API_KEY: str = ""

    # Groq (optional fast inference)
    GROQ_API_KEY: str = ""

    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"

    # App
    APP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    MAX_AUDIO_SIZE_MB: int = 25

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()

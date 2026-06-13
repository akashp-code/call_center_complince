import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    API_KEY: str = "sk_intel_987654321"
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    APP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    MAX_AUDIO_SIZE_MB: int = 25

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


def get_settings() -> Settings:
    return Settings(
        GROQ_API_KEY=os.environ.get("GROQ_API_KEY", ""),
        OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY", ""),
        API_KEY=os.environ.get("API_KEY", "sk_intel_987654321"),
        APP_ENV=os.environ.get("APP_ENV", "production"),
        LOG_LEVEL=os.environ.get("LOG_LEVEL", "INFO"),
    )
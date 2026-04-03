from pydantic import BaseModel, field_validator
from app.utils.enums import Language, AudioFormat


class CallAnalyticsRequest(BaseModel):
    language: Language
    audioFormat: AudioFormat = AudioFormat.MP3
    audioBase64: str

    @field_validator("audioBase64")
    @classmethod
    def validate_base64_not_empty(cls, v: str) -> str:
        if not v or len(v.strip()) < 100:
            raise ValueError("audioBase64 must be a valid, non-empty Base64 string.")
        return v.strip()

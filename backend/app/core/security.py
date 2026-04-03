from fastapi import Request, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from app.core.config import get_settings

settings = get_settings()

API_KEY_HEADER = APIKeyHeader(name="x-api-key", auto_error=False)


async def validate_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """
    Validates the x-api-key header.
    Raises 401 if missing or invalid.
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide 'x-api-key' in request headers.",
        )
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
        )
    return api_key

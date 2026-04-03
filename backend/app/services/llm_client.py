"""
llm_client.py — Shared LLM provider with automatic fallback chain.

Priority order:
  1. OpenAI (gpt-4o-mini)         — fastest, best JSON mode
  2. Groq  (llama-3.1-8b-instant) — free tier, fast inference
  3. Rule-based fallback           — if both APIs fail (bad keys, quota, etc.)

All services import get_llm_response() instead of creating their own OpenAI clients.
This means a single bad API key never crashes the pipeline.
"""

import json
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

_openai_client = None
_groq_client = None


def _get_openai():
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI
            _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        except Exception as e:
            logger.warning("openai_init_failed", error=str(e))
    return _openai_client


def _get_groq():
    global _groq_client
    if _groq_client is None:
        try:
            from groq import Groq
            _groq_client = Groq(api_key=settings.GROQ_API_KEY)
        except Exception as e:
            logger.warning("groq_init_failed", error=str(e))
    return _groq_client


def get_llm_response(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 500,
    temperature: float = 0.0,
    require_json: bool = False,
) -> str:
    """
    Sends a prompt to the best available LLM and returns the text response.

    Tries OpenAI first, then Groq, then returns empty string on total failure.
    Caller is responsible for parsing and handling empty/invalid responses.

    Args:
        system_prompt: Instructions for the model.
        user_prompt: The actual content to analyse.
        max_tokens: Max tokens in the response.
        temperature: Sampling temperature (0.0 = deterministic).
        require_json: If True, requests JSON mode (OpenAI only; Groq uses prompt hint).

    Returns:
        Raw string response from the model, or "" on failure.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # ── Attempt 1: OpenAI ────────────────────────────────────────────────────
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
        try:
            client = _get_openai()
            if client:
                kwargs = dict(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                if require_json:
                    kwargs["response_format"] = {"type": "json_object"}

                response = client.chat.completions.create(**kwargs)
                text = response.choices[0].message.content.strip()
                logger.info("llm_provider", provider="openai", tokens=len(text))
                return text
        except Exception as e:
            logger.warning("openai_failed_trying_groq", error=str(e))

    # ── Attempt 2: Groq ──────────────────────────────────────────────────────
    if settings.GROQ_API_KEY and len(settings.GROQ_API_KEY) > 10:
        try:
            client = _get_groq()
            if client:
                # Groq doesn't support response_format=json_object for all models,
                # so we append a JSON reminder to the system prompt when needed.
                groq_system = system_prompt
                if require_json:
                    groq_system += "\n\nIMPORTANT: Respond ONLY with valid JSON. No preamble, no markdown."

                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": groq_system},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                text = response.choices[0].message.content.strip()
                # Strip markdown code fences if Groq wraps JSON in them
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                    text = text.strip()
                logger.info("llm_provider", provider="groq", tokens=len(text))
                return text
        except Exception as e:
            logger.warning("groq_failed", error=str(e))

    # ── Attempt 3: Both APIs failed ──────────────────────────────────────────
    logger.error("all_llm_providers_failed", openai_key_set=bool(settings.OPENAI_API_KEY),
                 groq_key_set=bool(settings.GROQ_API_KEY))
    return ""

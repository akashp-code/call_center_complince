from app.core.logging import get_logger
from app.utils.helpers import timer
from app.services.llm_client import get_llm_response

logger = get_logger(__name__)

SUMMARIZER_SYSTEM_PROMPT = """You are an expert call center analyst.
Given a transcript of a customer service call (which may be in Hinglish or Tanglish - code-mixed Hindi/Tamil with English),
generate a concise, factual summary in English.

The summary should:
- Capture key facts: agent name, customer concern, product/service discussed, outcome
- Be 2-4 sentences maximum
- Be written in clear English
- Not add information not present in the transcript"""


def _rule_based_summary(transcript: str) -> str:
    """
    Fallback: extracts a basic summary from the transcript using simple heuristics.
    Used when all LLM providers are unavailable.
    """
    lines = [l.strip() for l in transcript.split("\n") if l.strip()]
    if not lines:
        return "Call transcript was processed. Summary unavailable due to service limitations."

    # Take first and last meaningful lines as a rough summary
    preview = lines[0] if lines else ""
    ending = lines[-1] if len(lines) > 1 else ""
    word_count = len(transcript.split())

    return (
        f"Call transcript processed ({word_count} words). "
        f"Opening: '{preview[:100]}'. "
        f"Closing: '{ending[:100]}'."
    )


@timer("summarize")
def summarize_transcript(transcript: str) -> str:
    """
    Generates a concise summary of the call transcript.
    Uses OpenAI → Groq → rule-based fallback chain.
    Never raises an exception.
    """
    if not transcript.strip():
        return "No transcript available for summarization."

    text = get_llm_response(
        system_prompt=SUMMARIZER_SYSTEM_PROMPT,
        user_prompt=f"Transcript:\n{transcript}",
        max_tokens=300,
        temperature=0.2,
        require_json=False,
    )

    if text:
        logger.info("summary_generated", chars=len(text), method="llm")
        return text

    # LLM completely unavailable — use rule-based fallback
    logger.warning("summary_using_rule_fallback")
    summary = _rule_based_summary(transcript)
    return summary

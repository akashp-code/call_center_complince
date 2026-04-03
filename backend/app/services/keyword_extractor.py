import json
import re
from collections import Counter
from app.core.logging import get_logger
from app.utils.helpers import timer
from app.services.llm_client import get_llm_response

logger = get_logger(__name__)

KEYWORD_SYSTEM_PROMPT = """You are a keyword extraction specialist for call center analytics.

Extract the most relevant and meaningful keywords from the provided call transcript and summary.

Rules:
- Extract 8-15 keywords/keyphrases
- Focus on: products, services, institutions, technical terms, financial terms, course names, tools, concepts
- Exclude: common words, filler words, pronouns
- Each keyword should be directly traceable to the transcript or summary
- Return them as a JSON array of strings

Example output:
{"keywords": ["Data Science", "IIT Madras", "EMI options", "Placement Support", "Career Change"]}"""

# Common stopwords for rule-based fallback
_STOPWORDS = {
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "they", "it",
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "was", "are", "were", "be", "been", "being", "have",
    "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "shall", "that", "this", "these", "those", "so", "if",
    "yes", "no", "ok", "okay", "um", "uh", "sir", "madam", "hello", "hi",
    "bye", "thank", "please", "just", "like", "know", "get", "got", "can",
    "not", "from", "about", "what", "when", "how", "there", "here", "also",
}


def _rule_based_keywords(transcript: str, summary: str) -> list:
    """
    TF-IDF-style keyword extraction without any external libraries.
    Used when all LLM providers are unavailable.
    """
    combined = f"{transcript} {summary}".lower()
    # Tokenise: keep words 3+ chars, remove punctuation
    words = re.findall(r"\b[a-zA-Z]{3,}\b", combined)
    meaningful = [w for w in words if w not in _STOPWORDS]

    # Count frequency and return top-12 by occurrence
    counts = Counter(meaningful)
    top = [word.capitalize() for word, _ in counts.most_common(12)]

    logger.info("keywords_rule_based", count=len(top))
    return top


@timer("keyword_extraction")
def extract_keywords(transcript: str, summary: str) -> list:
    """
    Extracts meaningful keywords from transcript + summary.
    Uses OpenAI → Groq → TF-IDF rule fallback. Never raises.
    """
    combined_text = f"Transcript:\n{transcript}\n\nSummary:\n{summary}"

    raw = get_llm_response(
        system_prompt=KEYWORD_SYSTEM_PROMPT,
        user_prompt=combined_text,
        max_tokens=200,
        temperature=0.1,
        require_json=True,
    )

    if raw:
        try:
            parsed = json.loads(raw)
            keywords = parsed.get("keywords", [])
            if isinstance(keywords, list) and keywords:
                seen = set()
                cleaned = []
                for kw in keywords:
                    kw_clean = str(kw).strip()
                    if kw_clean and kw_clean.lower() not in seen:
                        seen.add(kw_clean.lower())
                        cleaned.append(kw_clean)
                logger.info("keywords_extracted", count=len(cleaned), method="llm")
                return cleaned
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("keyword_parse_failed", error=str(e), raw=raw[:200])

    # LLM unavailable or returned invalid JSON — use rule-based fallback
    logger.warning("keywords_using_rule_fallback")
    return _rule_based_keywords(transcript, summary)


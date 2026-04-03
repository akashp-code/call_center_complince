import json
from app.core.logging import get_logger
from app.utils.helpers import timer
from app.utils.enums import PaymentPreference, RejectionReason, Sentiment
from app.services.llm_client import get_llm_response

logger = get_logger(__name__)


ANALYTICS_SYSTEM_PROMPT = """You are a business intelligence analyst for a call center.

Analyze the provided call transcript and extract the following business metrics:

1. PAYMENT PREFERENCE — How does the customer intend to pay (or how was payment discussed)?
   - "EMI": Customer wants to pay in installments over multiple months
   - "FULL_PAYMENT": Customer agrees to pay the full amount at once
   - "PARTIAL_PAYMENT": Customer wants to pay a portion now and the rest later
   - "DOWN_PAYMENT": Customer specifically mentions a down payment / advance
   - If no payment was discussed or intent is unclear, use "FULL_PAYMENT" as default.

2. REJECTION REASON — If the payment/sale was NOT completed, why?
   - "HIGH_INTEREST": Customer objects to interest rate or finds it expensive
   - "BUDGET_CONSTRAINTS": Customer says they don't have enough money right now
   - "ALREADY_PAID": Customer claims they have already paid
   - "NOT_INTERESTED": Customer is not interested in the product/service
   - "NONE": Payment was completed or no rejection occurred

3. SENTIMENT — Overall tone of the customer during the call:
   - "Positive": Cooperative, happy, agreeable
   - "Neutral": Neither positive nor negative, factual
   - "Negative": Frustrated, angry, dismissive

Respond ONLY with a valid JSON object:
{
  "paymentPreference": "EMI|FULL_PAYMENT|PARTIAL_PAYMENT|DOWN_PAYMENT",
  "rejectionReason": "HIGH_INTEREST|BUDGET_CONSTRAINTS|ALREADY_PAID|NOT_INTERESTED|NONE",
  "sentiment": "Positive|Neutral|Negative"
}"""


@timer("analytics")
def extract_analytics(transcript: str, summary: str) -> dict:
    """
    Extracts payment preference, rejection reason, and sentiment.
    Uses OpenAI → Groq → rule-based fallback chain. Never raises.
    """
    combined_text = f"Transcript:\n{transcript}\n\nSummary:\n{summary}"

    raw = get_llm_response(
        system_prompt=ANALYTICS_SYSTEM_PROMPT,
        user_prompt=combined_text,
        max_tokens=150,
        temperature=0.0,
        require_json=True,
    )

    if not raw:
        logger.warning("analytics_llm_unavailable_using_rule_fallback")
        return _rule_based_analytics(transcript)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("analytics_json_parse_failed", raw=raw[:200])
        return _rule_based_analytics(transcript)

    return _enforce_enums(parsed)


def _map_payment(value: str) -> str:
    """
    Fuzzy-maps any LLM payment string to a valid PaymentPreference enum value.
    Handles variants like 'installments', 'lump sum', 'advance', etc.
    """
    v = value.lower().strip()
    if any(kw in v for kw in ["emi", "installment", "monthly", "kist", "kiriya"]):
        return PaymentPreference.EMI.value
    if any(kw in v for kw in ["full", "lump", "one time", "onetime", "complete", "total"]):
        return PaymentPreference.FULL_PAYMENT.value
    if any(kw in v for kw in ["partial", "part", "some", "portion", "half"]):
        return PaymentPreference.PARTIAL_PAYMENT.value
    if any(kw in v for kw in ["down", "advance", "upfront", "initial", "deposit"]):
        return PaymentPreference.DOWN_PAYMENT.value
    # Try exact enum match as last resort
    try:
        return PaymentPreference(value).value
    except ValueError:
        logger.warning("payment_fuzzy_fallback", raw=value)
        return PaymentPreference.PARTIAL_PAYMENT.value  # safe fallback per spec


def _map_rejection(value: str) -> str:
    """
    Fuzzy-maps any LLM rejection string to a valid RejectionReason enum value.
    """
    v = value.lower().strip()
    if any(kw in v for kw in ["interest", "rate", "expensive", "costly", "high charge"]):
        return RejectionReason.HIGH_INTEREST.value
    if any(kw in v for kw in ["budget", "afford", "money", "funds", "financial", "broke", "short"]):
        return RejectionReason.BUDGET_CONSTRAINTS.value
    if any(kw in v for kw in ["already paid", "paid already", "already done", "settled"]):
        return RejectionReason.ALREADY_PAID.value
    if any(kw in v for kw in ["not interested", "no interest", "don't want", "dont want", "reject"]):
        return RejectionReason.NOT_INTERESTED.value
    if any(kw in v for kw in ["none", "no rejection", "completed", "success", "n/a"]):
        return RejectionReason.NONE.value
    # Try exact enum match
    try:
        return RejectionReason(value).value
    except ValueError:
        logger.warning("rejection_fuzzy_fallback", raw=value)
        return RejectionReason.NONE.value


def _map_sentiment(value: str) -> str:
    """
    Fuzzy-maps any LLM sentiment string to Positive / Neutral / Negative.
    """
    v = value.lower().strip()
    if any(kw in v for kw in ["positive", "happy", "good", "satisfied", "pleased", "cooperative"]):
        return Sentiment.POSITIVE.value
    if any(kw in v for kw in ["negative", "angry", "frustrated", "upset", "unhappy", "annoyed"]):
        return Sentiment.NEGATIVE.value
    if any(kw in v for kw in ["neutral", "mixed", "indifferent", "ok", "okay", "moderate"]):
        return Sentiment.NEUTRAL.value
    # Try exact enum match
    try:
        return Sentiment(value).value
    except ValueError:
        logger.warning("sentiment_fuzzy_fallback", raw=value)
        return Sentiment.NEUTRAL.value


def _enforce_enums(parsed: dict) -> dict:
    """
    Two-layer enforcement:
      1. Fuzzy string mapping (handles LLM variants like 'installments', 'lump sum')
      2. Final strict enum validation (guarantee only valid values reach the response)
    """
    payment_raw = str(parsed.get("paymentPreference", "")).strip()
    rejection_raw = str(parsed.get("rejectionReason", "")).strip()
    sentiment_raw = str(parsed.get("sentiment", "")).strip()

    payment = _map_payment(payment_raw)
    rejection = _map_rejection(rejection_raw)
    sentiment = _map_sentiment(sentiment_raw)

    logger.info("analytics_result", payment=payment, rejection=rejection, sentiment=sentiment)

    return {
        "paymentPreference": payment,
        "rejectionReason": rejection,
        "sentiment": sentiment,
    }


def _rule_based_analytics(transcript: str) -> dict:
    """
    Pure keyword-based analytics when all LLMs are unavailable.
    Uses the same keyword lists as the fuzzy mappers for consistency.
    """
    t = transcript.lower()

    # Payment preference
    if any(kw in t for kw in ["emi", "installment", "monthly", "kist"]):
        payment = PaymentPreference.EMI.value
    elif any(kw in t for kw in ["full payment", "full amount", "lump sum", "one time"]):
        payment = PaymentPreference.FULL_PAYMENT.value
    elif any(kw in t for kw in ["down payment", "advance", "deposit", "upfront"]):
        payment = PaymentPreference.DOWN_PAYMENT.value
    elif any(kw in t for kw in ["partial", "some amount", "part payment"]):
        payment = PaymentPreference.PARTIAL_PAYMENT.value
    else:
        payment = PaymentPreference.PARTIAL_PAYMENT.value  # spec default

    # Rejection reason
    if any(kw in t for kw in ["already paid", "paid already", "already done"]):
        rejection = RejectionReason.ALREADY_PAID.value
    elif any(kw in t for kw in ["interest", "rate too high", "expensive", "costly"]):
        rejection = RejectionReason.HIGH_INTEREST.value
    elif any(kw in t for kw in ["no money", "can't afford", "budget", "financial problem"]):
        rejection = RejectionReason.BUDGET_CONSTRAINTS.value
    elif any(kw in t for kw in ["not interested", "don't want", "no thanks", "reject"]):
        rejection = RejectionReason.NOT_INTERESTED.value
    else:
        rejection = RejectionReason.NONE.value

    # Sentiment — simple polarity keywords
    positive_words = ["thank", "great", "okay", "sure", "yes", "good", "happy", "agree"]
    negative_words = ["angry", "upset", "frustrated", "no", "refuse", "never", "worst"]
    pos = sum(1 for w in positive_words if w in t)
    neg = sum(1 for w in negative_words if w in t)
    if pos > neg:
        sentiment = Sentiment.POSITIVE.value
    elif neg > pos:
        sentiment = Sentiment.NEGATIVE.value
    else:
        sentiment = Sentiment.NEUTRAL.value

    logger.info("analytics_rule_based", payment=payment, rejection=rejection, sentiment=sentiment)
    return {"paymentPreference": payment, "rejectionReason": rejection, "sentiment": sentiment}


def _safe_defaults() -> dict:
    return {
        "paymentPreference": PaymentPreference.PARTIAL_PAYMENT.value,  # spec-specified fallback
        "rejectionReason": RejectionReason.NONE.value,
        "sentiment": Sentiment.NEUTRAL.value,
    }

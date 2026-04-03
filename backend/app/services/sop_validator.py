import json
from app.core.logging import get_logger
from app.utils.helpers import timer
from app.utils.enums import AdherenceStatus
from app.services.llm_client import get_llm_response
logger = get_logger(__name__)

# ── Rule-based detectors ───────────────────────────────────────────────────────
# Broad keyword lists cover English, Hindi (Hinglish) and Tamil (Tanglish) variants.

def _detect_greeting(text: str) -> bool:
    keywords = [
        "hello", "hi", "hey", "vanakkam", "namaste", "namaskar",
        "good morning", "good afternoon", "good evening",
        "welcome", "greetings", "halo", "hai",
    ]
    t = text.lower()
    return any(kw in t for kw in keywords)


def _detect_identification(text: str) -> bool:
    keywords = [
        "calling from", "this is", "i am", "i'm", "my name is",
        "speaking from", "on behalf of", "representing",
        "can i speak to", "am i speaking", "is this",
        "naan", "ennoda peyar", "mera naam",
    ]
    t = text.lower()
    return any(kw in t for kw in keywords)


def _detect_problem(text: str) -> bool:
    keywords = [
        "issue", "problem", "regarding", "concern", "reason for",
        "calling about", "help you with", "matter", "query",
        "emi", "payment", "due", "outstanding", "pending",
        "pathi", "vishayam", "baat",
    ]
    t = text.lower()
    return any(kw in t for kw in keywords)


def _detect_solution(text: str) -> bool:
    keywords = [
        "offer", "we can", "solution", "suggest", "recommend",
        "option", "plan", "arrangement", "assist", "help",
        "provide", "available", "waiver", "discount", "settle",
        "thara", "seyyalam", "kar sakte",
    ]
    t = text.lower()
    return any(kw in t for kw in keywords)


def _detect_closing(text: str) -> bool:
    keywords = [
        "thank you", "thanks", "bye", "goodbye", "good bye",
        "have a good", "have a nice", "take care",
        "nandri", "dhanyavaad", "shukriya", "alvida",
    ]
    t = text.lower()
    return any(kw in t for kw in keywords)


# ── Rule-based batch runner ────────────────────────────────────────────────────

def _run_rule_based(transcript: str) -> dict:
    """Returns a dict of bool flags from rule-based keyword matching."""
    return {
        "greeting": _detect_greeting(transcript),
        "identification": _detect_identification(transcript),
        "problemStatement": _detect_problem(transcript),
        "solutionOffering": _detect_solution(transcript),
        "closing": _detect_closing(transcript),
    }


# ── LLM-based validator ────────────────────────────────────────────────────────

SOP_SYSTEM_PROMPT = """You are a strict call center compliance auditor.

Analyze the call transcript and determine if the agent followed the standard SOP script:
1. GREETING — Agent greets the customer (Hello, Vanakkam, Namaste, Hi, etc.)
2. IDENTIFICATION — Agent identifies themselves (name, company) AND confirms customer identity
3. PROBLEM STATEMENT — Agent clearly states the purpose of the call or addresses the customer's issue
4. SOLUTION OFFERING — Agent proposes a solution, plan, option, or next step
5. CLOSING — Agent wraps up the call with a proper closing (Thank you, Goodbye, etc.)

Respond ONLY with a valid JSON object in this exact format:
{
  "greeting": true or false,
  "identification": true or false,
  "problemStatement": true or false,
  "solutionOffering": true or false,
  "closing": true or false,
  "explanation": "One sentence explaining any missing or failed SOP steps."
}

Be strict: identification requires BOTH agent self-identification AND customer confirmation."""


def _run_llm_based(transcript: str) -> dict:
    """Calls the best available LLM to validate SOP flags. Returns parsed dict or {} on failure."""
    raw = get_llm_response(
        system_prompt=SOP_SYSTEM_PROMPT,
        user_prompt=f"Transcript:\n{transcript}",
        max_tokens=300,
        temperature=0.0,
        require_json=True,
    )
    if not raw:
        logger.warning("sop_llm_empty_response")
        return {}
    logger.info("sop_llm_raw", raw=raw[:200])
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("sop_llm_json_parse_failed", raw=raw[:200])
        return {}


# ── Public API ─────────────────────────────────────────────────────────────────

@timer("sop_validation")
def validate_sop(transcript: str) -> dict:
    """
    Hybrid SOP validator: rule-based OR LLM.
    A stage is TRUE if EITHER the rule detector OR the LLM says it is present.
    This ensures maximum recall — a missed keyword doesn't lose points.
    """
    if not transcript.strip():
        return _build_result(False, False, False, False, False,
                             "Empty transcript — no SOP analysis possible.")

    # ── Rule-based pass ──────────────────────────────────────────────────────
    rule_flags = _run_rule_based(transcript)
    logger.info("sop_rule_flags", **rule_flags)

    # ── LLM pass (best-effort; falls back to empty dict on failure) ──────────
    try:
        llm_parsed = _run_llm_based(transcript)
    except Exception as e:
        logger.warning("sop_llm_failed_using_rules_only", error=str(e))
        llm_parsed = {}

    # ── Merge: rule OR llm (whichever is more generous) ─────────────────────
    def merge(key: str) -> bool:
        rule_val = rule_flags.get(key, False)
        llm_val = bool(llm_parsed.get(key, False))
        return rule_val or llm_val

    greeting = merge("greeting")
    identification = merge("identification")
    problem = merge("problemStatement")
    solution = merge("solutionOffering")
    closing = merge("closing")
    explanation = str(llm_parsed.get("explanation", "")).strip() or \
                  "SOP checked via hybrid rule + LLM analysis."

    return _build_result(greeting, identification, problem, solution, closing, explanation)


# ── Result builder ─────────────────────────────────────────────────────────────

def _build_result(
    greeting: bool,
    identification: bool,
    problem: bool,
    solution: bool,
    closing: bool,
    explanation: str,
) -> dict:
    """Assembles the final SOP validation result dict with strict typing."""
    flags = [greeting, identification, problem, solution, closing]
    true_count = sum(flags)
    score = round(true_count / 5, 2)
    status = AdherenceStatus.FOLLOWED if all(flags) else AdherenceStatus.NOT_FOLLOWED

    logger.info(
        "sop_final_result",
        score=score,
        status=status.value,
        greeting=greeting,
        identification=identification,
        problem=problem,
        solution=solution,
        closing=closing,
    )

    return {
        "greeting": bool(greeting),
        "identification": bool(identification),
        "problemStatement": bool(problem),
        "solutionOffering": bool(solution),
        "closing": bool(closing),
        "complianceScore": float(score),
        "adherenceStatus": str(status.value),
        "explanation": str(explanation),
    }

"""
Test suite for Call Center Compliance API.

Run with:
    pytest tests/ -v
"""

import base64
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import get_settings

settings = get_settings()
client = TestClient(app)

VALID_HEADERS = {"x-api-key": settings.API_KEY, "Content-Type": "application/json"}

# ── Minimal valid Base64 MP3 (silent 1-second MP3) ───────────────────────────
# In real tests, load an actual audio file. This is a placeholder.
DUMMY_B64 = base64.b64encode(b"\xff\xfb\x90\x00" * 500).decode()

MOCK_PIPELINE_RESULT = {
    "status": "success",
    "language": "Tamil",
    "transcript": "Agent: Vanakkam. Customer: Hello. Agent: Your EMI is pending.",
    "summary": "Agent reminded customer about pending EMI payment.",
    "sop_validation": {
        "greeting": True,
        "identification": False,
        "problemStatement": True,
        "solutionOffering": True,
        "closing": True,
        "complianceScore": 0.8,
        "adherenceStatus": "NOT_FOLLOWED",
        "explanation": "Identification step was missing.",
    },
    "analytics": {
        "paymentPreference": "EMI",
        "rejectionReason": "BUDGET_CONSTRAINTS",
        "sentiment": "Neutral",
    },
    "keywords": ["EMI", "pending payment", "Vanakkam"],
}


# ── Authentication tests ──────────────────────────────────────────────────────

def test_missing_api_key_returns_401():
    resp = client.post("/api/v1/call-analytics", json={
        "language": "Tamil",
        "audioFormat": "mp3",
        "audioBase64": DUMMY_B64,
    })
    assert resp.status_code == 401


def test_invalid_api_key_returns_401():
    resp = client.post("/api/v1/call-analytics",
                       headers={"x-api-key": "WRONG_KEY"},
                       json={"language": "Tamil", "audioFormat": "mp3", "audioBase64": DUMMY_B64})
    assert resp.status_code == 401


def test_valid_api_key_is_accepted():
    with patch("app.api.v1.routes.process_call_task") as mock_task:
        mock_result = MagicMock()
        mock_result.get.return_value = MOCK_PIPELINE_RESULT
        mock_task.apply_async.return_value = mock_result

        resp = client.post("/api/v1/call-analytics",
                           headers=VALID_HEADERS,
                           json={"language": "Tamil", "audioFormat": "mp3", "audioBase64": DUMMY_B64})
        assert resp.status_code == 200


# ── Request validation tests ──────────────────────────────────────────────────

def test_missing_audio_returns_422():
    resp = client.post("/api/v1/call-analytics",
                       headers=VALID_HEADERS,
                       json={"language": "Tamil", "audioFormat": "mp3"})
    assert resp.status_code == 422


def test_invalid_language_returns_422():
    resp = client.post("/api/v1/call-analytics",
                       headers=VALID_HEADERS,
                       json={"language": "French", "audioFormat": "mp3", "audioBase64": DUMMY_B64})
    assert resp.status_code == 422


def test_short_base64_returns_422():
    resp = client.post("/api/v1/call-analytics",
                       headers=VALID_HEADERS,
                       json={"language": "Hindi", "audioFormat": "mp3", "audioBase64": "abc"})
    assert resp.status_code == 422


# ── Response structure tests ──────────────────────────────────────────────────

def test_response_has_all_required_fields():
    with patch("app.api.v1.routes.process_call_task") as mock_task:
        mock_result = MagicMock()
        mock_result.get.return_value = MOCK_PIPELINE_RESULT
        mock_task.apply_async.return_value = mock_result

        resp = client.post("/api/v1/call-analytics",
                           headers=VALID_HEADERS,
                           json={"language": "Tamil", "audioFormat": "mp3", "audioBase64": DUMMY_B64})
        assert resp.status_code == 200
        data = resp.json()

        required_top = ["status", "language", "transcript", "summary", "sop_validation", "analytics", "keywords"]
        for field in required_top:
            assert field in data, f"Missing top-level field: {field}"

        required_sop = ["greeting", "identification", "problemStatement", "solutionOffering",
                        "closing", "complianceScore", "adherenceStatus", "explanation"]
        for field in required_sop:
            assert field in data["sop_validation"], f"Missing SOP field: {field}"

        required_analytics = ["paymentPreference", "rejectionReason", "sentiment"]
        for field in required_analytics:
            assert field in data["analytics"], f"Missing analytics field: {field}"


def test_payment_preference_valid_enum():
    with patch("app.api.v1.routes.process_call_task") as mock_task:
        mock_result = MagicMock()
        mock_result.get.return_value = MOCK_PIPELINE_RESULT
        mock_task.apply_async.return_value = mock_result

        resp = client.post("/api/v1/call-analytics",
                           headers=VALID_HEADERS,
                           json={"language": "Tamil", "audioFormat": "mp3", "audioBase64": DUMMY_B64})
        data = resp.json()
        assert data["analytics"]["paymentPreference"] in [
            "EMI", "FULL_PAYMENT", "PARTIAL_PAYMENT", "DOWN_PAYMENT"
        ]


def test_rejection_reason_valid_enum():
    with patch("app.api.v1.routes.process_call_task") as mock_task:
        mock_result = MagicMock()
        mock_result.get.return_value = MOCK_PIPELINE_RESULT
        mock_task.apply_async.return_value = mock_result

        resp = client.post("/api/v1/call-analytics",
                           headers=VALID_HEADERS,
                           json={"language": "Tamil", "audioFormat": "mp3", "audioBase64": DUMMY_B64})
        data = resp.json()
        assert data["analytics"]["rejectionReason"] in [
            "HIGH_INTEREST", "BUDGET_CONSTRAINTS", "ALREADY_PAID", "NOT_INTERESTED", "NONE"
        ]


def test_sentiment_valid_enum():
    with patch("app.api.v1.routes.process_call_task") as mock_task:
        mock_result = MagicMock()
        mock_result.get.return_value = MOCK_PIPELINE_RESULT
        mock_task.apply_async.return_value = mock_result

        resp = client.post("/api/v1/call-analytics",
                           headers=VALID_HEADERS,
                           json={"language": "Tamil", "audioFormat": "mp3", "audioBase64": DUMMY_B64})
        data = resp.json()
        assert data["analytics"]["sentiment"] in ["Positive", "Neutral", "Negative"]


def test_compliance_score_range():
    with patch("app.api.v1.routes.process_call_task") as mock_task:
        mock_result = MagicMock()
        mock_result.get.return_value = MOCK_PIPELINE_RESULT
        mock_task.apply_async.return_value = mock_result

        resp = client.post("/api/v1/call-analytics",
                           headers=VALID_HEADERS,
                           json={"language": "Tamil", "audioFormat": "mp3", "audioBase64": DUMMY_B64})
        data = resp.json()
        score = data["sop_validation"]["complianceScore"]
        assert 0.0 <= score <= 1.0, f"Score out of range: {score}"


def test_adherence_status_valid():
    with patch("app.api.v1.routes.process_call_task") as mock_task:
        mock_result = MagicMock()
        mock_result.get.return_value = MOCK_PIPELINE_RESULT
        mock_task.apply_async.return_value = mock_result

        resp = client.post("/api/v1/call-analytics",
                           headers=VALID_HEADERS,
                           json={"language": "Tamil", "audioFormat": "mp3", "audioBase64": DUMMY_B64})
        data = resp.json()
        assert data["sop_validation"]["adherenceStatus"] in ["FOLLOWED", "NOT_FOLLOWED"]


def test_keywords_is_non_empty_list():
    with patch("app.api.v1.routes.process_call_task") as mock_task:
        mock_result = MagicMock()
        mock_result.get.return_value = MOCK_PIPELINE_RESULT
        mock_task.apply_async.return_value = mock_result

        resp = client.post("/api/v1/call-analytics",
                           headers=VALID_HEADERS,
                           json={"language": "Tamil", "audioFormat": "mp3", "audioBase64": DUMMY_B64})
        data = resp.json()
        assert isinstance(data["keywords"], list)
        assert len(data["keywords"]) > 0


# ── Unit tests for enums ──────────────────────────────────────────────────────

def test_enums():
    from app.utils.enums import PaymentPreference, RejectionReason, Sentiment, AdherenceStatus
    assert PaymentPreference("EMI") == PaymentPreference.EMI
    assert RejectionReason("NONE") == RejectionReason.NONE
    assert Sentiment("Positive") == Sentiment.POSITIVE
    assert AdherenceStatus("FOLLOWED") == AdherenceStatus.FOLLOWED


# ── Health check ──────────────────────────────────────────────────────────────

def test_health_check():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

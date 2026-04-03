from pydantic import BaseModel
from typing import List, Optional
from app.utils.enums import (
    Language, PaymentPreference, RejectionReason,
    Sentiment, AdherenceStatus, ResponseStatus
)


class SOPValidation(BaseModel):
    greeting: bool
    identification: bool
    problemStatement: bool
    solutionOffering: bool
    closing: bool
    complianceScore: float
    adherenceStatus: AdherenceStatus
    explanation: str


class Analytics(BaseModel):
    paymentPreference: PaymentPreference
    rejectionReason: RejectionReason
    sentiment: Sentiment


class CallAnalyticsResponse(BaseModel):
    status: ResponseStatus
    language: str           # str (not enum) to accommodate Whisper-detected language codes
    transcript: str
    summary: str
    sop_validation: SOPValidation
    analytics: Analytics
    keywords: List[str]
    processingTime: Optional[str] = None   # Issue 7: e.g. "12.34s"


class ErrorResponse(BaseModel):
    status: ResponseStatus = ResponseStatus.ERROR
    message: str
    detail: Optional[str] = None


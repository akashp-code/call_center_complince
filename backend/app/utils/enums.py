from enum import Enum


class Language(str, Enum):
    TAMIL = "Tamil"
    HINDI = "Hindi"


class AudioFormat(str, Enum):
    MP3 = "mp3"


class PaymentPreference(str, Enum):
    EMI = "EMI"
    FULL_PAYMENT = "FULL_PAYMENT"
    PARTIAL_PAYMENT = "PARTIAL_PAYMENT"
    DOWN_PAYMENT = "DOWN_PAYMENT"


class RejectionReason(str, Enum):
    HIGH_INTEREST = "HIGH_INTEREST"
    BUDGET_CONSTRAINTS = "BUDGET_CONSTRAINTS"
    ALREADY_PAID = "ALREADY_PAID"
    NOT_INTERESTED = "NOT_INTERESTED"
    NONE = "NONE"


class Sentiment(str, Enum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"


class AdherenceStatus(str, Enum):
    FOLLOWED = "FOLLOWED"
    NOT_FOLLOWED = "NOT_FOLLOWED"


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"

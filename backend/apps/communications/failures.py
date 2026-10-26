"""
Communication Failure Classification and Humanization Layer.
Clean Architecture + SOLID.
Translates technical provider faults, network exceptions, and carrier rejections
into clear, actionable, recruiter-friendly explanations.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class FailureCategory(str, Enum):
    """Normalized categories for communication failures."""
    INVALID_RECIPIENT = "invalid_recipient"
    TEMPORARY_PROVIDER_FAILURE = "temporary_provider_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    DELIVERY_FAILURE = "delivery_failure"
    SERVICE_UNAVAILABLE = "service_unavailable"
    OTHER_PROVIDER_ERROR = "other_provider_error"


RETRYABLE_FAILURE_CATEGORIES = frozenset({
    FailureCategory.TEMPORARY_PROVIDER_FAILURE.value,
    FailureCategory.RATE_LIMIT_EXCEEDED.value,
    FailureCategory.DELIVERY_FAILURE.value,
    FailureCategory.SERVICE_UNAVAILABLE.value,
})

PERMANENT_FAILURE_CATEGORIES = frozenset({
    FailureCategory.INVALID_RECIPIENT.value,
    FailureCategory.OTHER_PROVIDER_ERROR.value,
})


def is_retryable_failure(category: Optional[str]) -> bool:
    """
    Permanent failures (invalid recipient / provider policy) cannot be retried.
    Transient and unknown categories can be retried.
    """
    if category in PERMANENT_FAILURE_CATEGORIES:
        return False
    return True


@dataclass(frozen=True)
class FailureAnalysis:
    """Structured humanized failure explanation for recruiters."""
    category: FailureCategory
    category_label: str
    recruiter_message: str
    technical_details: str
    is_retryable: bool


class CommunicationFailureTranslator:
    """
    Translates raw provider responses, HTTP status codes, and exceptions
    into meaningful recruiter-facing messages (Requirement #8).
    """

    @classmethod
    def translate(
        cls,
        channel: str,
        recipient: Optional[str] = None,
        status_code: Optional[int] = None,
        raw_error: Optional[str] = None,
        exception: Optional[Exception] = None,
    ) -> FailureAnalysis:
        raw_text = (str(raw_error) if raw_error else "") or (str(exception) if exception else "")
        raw_lower = raw_text.lower()
        clean_recipient = (recipient or "").strip()

        # 1. Invalid Recipient
        # Examples: Empty phone, malformed characters, test fail numbers, E.164 mismatch
        if (
            not clean_recipient
            or (channel in ("sms", "whatsapp") and not cls._is_valid_phone(clean_recipient))
            or (channel == "email" and "@" not in clean_recipient)
            or "invalid recipient" in raw_lower
            or "invalid msisdn" in raw_lower
            or "invalid phone" in raw_lower
            or "unregistered" in raw_lower
            or "recipient rejected" in raw_lower
            or clean_recipient.startswith("0000")
            or "fail_number" in clean_recipient.lower()
        ):
            return FailureAnalysis(
                category=FailureCategory.INVALID_RECIPIENT,
                category_label="Invalid Recipient",
                recruiter_message=(
                    f"Invalid recipient contact: '{clean_recipient or 'Empty'}' is not a valid destination "
                    f"for {channel.upper()}. Please verify the candidate's phone number and country code."
                ),
                technical_details=raw_text or "Invalid destination contact format or inactive subscriber.",
                is_retryable=False,
            )

        # 2. Rate Limiting (HTTP 429 or provider throttle)
        if (
            status_code == 429
            or "429" in raw_lower
            or "rate limit" in raw_lower
            or "too many requests" in raw_lower
            or "throttled" in raw_lower
            or "quota exceeded" in raw_lower
        ):
            return FailureAnalysis(
                category=FailureCategory.RATE_LIMIT_EXCEEDED,
                category_label="Rate Limit Exceeded",
                recruiter_message=(
                    f"Sending limit reached: The communication provider's dispatch rate for {channel.upper()} "
                    f"has been temporarily exceeded. Please wait a few moments before sending more messages."
                ),
                technical_details=raw_text or f"HTTP 429: Provider rate limit exceeded on {channel}.",
                is_retryable=True,
            )

        # 3. Temporary Provider Failure (502, 503, 504, Gateway Timeout)
        if (
            status_code in (502, 503, 504)
            or "503" in raw_lower
            or "504" in raw_lower
            or "temporary" in raw_lower
            or "downstream timeout" in raw_lower
            or "gateway timeout" in raw_lower
            or "retryable" in raw_lower
            or "[temp_fail]" in raw_lower
        ):
            return FailureAnalysis(
                category=FailureCategory.TEMPORARY_PROVIDER_FAILURE,
                category_label="Temporary Provider Failure",
                recruiter_message=(
                    "Temporary provider delay: The downstream telecommunication network experienced a momentary interruption. "
                    "This message can be safely retried shortly."
                ),
                technical_details=raw_text or f"HTTP {status_code or 503}: Downstream gateway timeout.",
                is_retryable=True,
            )

        # 4. Communication Service Unavailable (Connection Refused, Network Down)
        if (
            "connection refused" in raw_lower
            or "failed to establish a new connection" in raw_lower
            or "max retries exceeded" in raw_lower
            or "network is unreachable" in raw_lower
            or "service unavailable" in raw_lower
            or "actively refused" in raw_lower
            or "name or service not known" in raw_lower
        ):
            return FailureAnalysis(
                category=FailureCategory.SERVICE_UNAVAILABLE,
                category_label="Service Unavailable",
                recruiter_message=(
                    f"Communication service unavailable: Could not establish a connection to the {channel.upper()} provider. "
                    f"Please verify that the messaging gateway is running."
                ),
                technical_details=raw_text or "Network connection refused / gateway offline.",
                is_retryable=True,
            )

        # 5. Message Delivery Failure (Handset off, carrier undeliverable, spam block)
        if (
            "undeliverable" in raw_lower
            or "delivery failure" in raw_lower
            or "carrier rejected" in raw_lower
            or "inactive subscriber" in raw_lower
            or "unreachable" in raw_lower
            or "handset" in raw_lower
            or "blocked" in raw_lower
            or "delivery_failed" in raw_lower
        ):
            return FailureAnalysis(
                category=FailureCategory.DELIVERY_FAILURE,
                category_label="Message Delivery Failure",
                recruiter_message=(
                    "Delivery failed: The candidate's mobile carrier could not deliver the message to the device. "
                    "The handset may be turned off, out of network coverage, or blocked by carrier filters."
                ),
                technical_details=raw_text or "Carrier undeliverable status received.",
                is_retryable=True,
            )

        # 6. Other Provider-Related Errors (WhatsApp template rejection, auth/account failure, sandbox)
        return FailureAnalysis(
            category=FailureCategory.OTHER_PROVIDER_ERROR,
            category_label="Provider Processing Error",
            recruiter_message=(
                f"Provider error: The {channel.upper()} provider rejected this transmission. "
                f"Please verify message template approval or provider account status."
            ),
            technical_details=raw_text or "Unspecified provider error response.",
            is_retryable=False,
        )

    @staticmethod
    def _is_valid_phone(phone: str) -> bool:
        """Validates phone has digits and reasonable length (e.g. 7 to 15 digits)."""
        digits = "".join([c for c in phone if c.isdigit()])
        return 7 <= len(digits) <= 15

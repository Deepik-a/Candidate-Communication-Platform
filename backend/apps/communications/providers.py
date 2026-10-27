"""
Concrete Communication Providers implementing CommunicationProvider interface.
Infrastructure layer (Clean Architecture + Open/Closed Principle + Liskov Substitution Principle).

Supports:
1. Dummy Independent Communication Provider (HTTP microservice on port 9000)
   - Send messages & receive reference IDs
   - Webhook-based status updates (Sent → Delivered → Read)
   - Simulates successful messages, failures, and temporary provider outages
2. Mock In-Memory Provider (internal fallback for tests / offline dev)
"""

import uuid
import logging
from typing import Dict, Optional
import requests
from decouple import config

from .domain import CommunicationProvider, ProviderMessageResult, DeliveryStatus
from .failures import CommunicationFailureTranslator

logger = logging.getLogger(__name__)


class DummyServiceCommunicationProvider(CommunicationProvider):
    """
    Adapter for the independent dummy communication microservice.
    Communicates over HTTP with the standalone dummy_provider/server.py process.

    Capabilities (matching all project requirements for a dummy provider):
    - POST /messages/send      → send a message, get reference_id back
    - GET  /messages/{id}/status → poll current delivery status
    - GET  /health             → provider health check
    - Webhooks fired by the dummy service update backend status in real-time
    - Simulates: success, failure, temporary outage (503), rate-limit (429)
    """

    def __init__(self, base_url: Optional[str] = None):
        self._base_url = (base_url or config("DUMMY_PROVIDER_URL", default="http://localhost:9000")).rstrip("/")
        self._name = "dummy-service"

    @property
    def provider_name(self) -> str:
        return self._name

    def send(self, recipient: str, content: str, channel: str) -> ProviderMessageResult:
        url = f"{self._base_url}/messages/send"
        payload = {
            "recipient": recipient,
            "content": content,
            "channel": channel,
        }

        try:
            resp = requests.post(url, json=payload, timeout=5)

            # 429 Rate Limit — simulated by dummy provider's rate_limit mode
            if resp.status_code == 429:
                analysis = CommunicationFailureTranslator.translate(
                    channel=channel,
                    recipient=recipient,
                    status_code=429,
                    raw_error="HTTP 429 Rate limit exceeded. Too many requests in time window.",
                )
                return ProviderMessageResult(
                    success=False,
                    status=DeliveryStatus.FAILED,
                    provider_name=self._name,
                    provider_message_id=f"rate_limit_{uuid.uuid4().hex[:8]}",
                    failure_category=analysis.category.value,
                    error_message=analysis.recruiter_message,
                    technical_details=analysis.technical_details,
                )

            # 502 / 503 / 504 Temporary failure — simulated by dummy provider's temporary_failure mode
            if resp.status_code in (502, 503, 504):
                err_data = {}
                try:
                    err_data = resp.json()
                except Exception:
                    pass
                err_msg = err_data.get("error", "Temporary downstream provider unavailable.")
                analysis = CommunicationFailureTranslator.translate(
                    channel=channel,
                    recipient=recipient,
                    status_code=resp.status_code,
                    raw_error=err_msg,
                )
                return ProviderMessageResult(
                    success=False,
                    status=DeliveryStatus.FAILED,
                    provider_name=self._name,
                    provider_message_id=f"temp_fail_{uuid.uuid4().hex[:8]}",
                    failure_category=analysis.category.value,
                    error_message=analysis.recruiter_message,
                    technical_details=analysis.technical_details,
                )

            # Parse JSON response
            try:
                data = resp.json()
            except Exception:
                data = {}

            is_success = data.get("success", False)
            raw_status = data.get("status", "failed")
            ref_id = data.get("reference_id", f"ref_{uuid.uuid4().hex[:8]}")
            err = data.get("error")

            status_map = {
                "sent": DeliveryStatus.SENT,
                "delivered": DeliveryStatus.DELIVERED,
                "read": DeliveryStatus.READ,
                "failed": DeliveryStatus.FAILED,
            }
            mapped_status = status_map.get(raw_status, DeliveryStatus.FAILED)

            if not is_success or mapped_status == DeliveryStatus.FAILED:
                analysis = CommunicationFailureTranslator.translate(
                    channel=channel,
                    recipient=recipient,
                    status_code=resp.status_code,
                    raw_error=err,
                )
                return ProviderMessageResult(
                    success=False,
                    status=DeliveryStatus.FAILED,
                    provider_name=self._name,
                    provider_message_id=ref_id,
                    failure_category=analysis.category.value,
                    error_message=analysis.recruiter_message,
                    technical_details=analysis.technical_details,
                )

            return ProviderMessageResult(
                success=True,
                status=mapped_status,
                provider_name=self._name,
                provider_message_id=ref_id,
                failure_category="",
                error_message=None,
                technical_details=None,
            )

        except requests.exceptions.RequestException as e:
            analysis = CommunicationFailureTranslator.translate(
                channel=channel,
                recipient=recipient,
                exception=e,
                raw_error="Communication service unavailable: dummy provider is not reachable.",
            )
            return ProviderMessageResult(
                success=False,
                status=DeliveryStatus.FAILED,
                provider_name=self._name,
                provider_message_id=f"unavailable_{uuid.uuid4().hex[:8]}",
                failure_category=analysis.category.value,
                error_message=analysis.recruiter_message,
                technical_details=str(e),
            )

    def health(self) -> dict:
        url = f"{self._base_url}/health"
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                data = {}
                try:
                    data = resp.json()
                except Exception:
                    pass
                return {
                    "id": "dummy",
                    "name": "Dummy Communication Service",
                    "status": "operational",
                    "detail": data.get("status", "Service is healthy and ready to accept messages."),
                    "base_url": self._base_url,
                }
            return {
                "id": "dummy",
                "name": "Dummy Communication Service",
                "status": "degraded",
                "detail": f"Health endpoint returned HTTP {resp.status_code}.",
                "base_url": self._base_url,
            }
        except requests.exceptions.RequestException as e:
            return {
                "id": "dummy",
                "name": "Dummy Communication Service",
                "status": "unavailable",
                "detail": (
                    "The dummy communication provider is not running. "
                    "Start it with: python dummy_provider/server.py"
                ),
                "base_url": self._base_url,
                "error": str(e),
            }

    def check_status(self, provider_message_id: str) -> DeliveryStatus:
        url = f"{self._base_url}/messages/{provider_message_id}/status"
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                raw = data.get("status", "sent")
                status_map = {
                    "sent": DeliveryStatus.SENT,
                    "delivered": DeliveryStatus.DELIVERED,
                    "read": DeliveryStatus.READ,
                    "failed": DeliveryStatus.FAILED,
                }
                return status_map.get(raw, DeliveryStatus.SENT)
        except Exception:
            pass
        return DeliveryStatus.SENT


class MockCommunicationProvider(CommunicationProvider):
    """
    In-memory fallback provider for local development and automated tests.
    Does not make any HTTP calls — purely simulates delivery in-process.
    Simulates failures when content contains '[fail]' or recipient starts with '0000'.
    """

    def __init__(self, provider_name: str = "mock-gateway"):
        self._provider_name = provider_name
        self._status_store: Dict[str, DeliveryStatus] = {}

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def send(self, recipient: str, content: str, channel: str) -> ProviderMessageResult:
        msg_id = f"mock_{channel}_{uuid.uuid4().hex[:10]}"

        if "[fail]" in content.lower() or recipient.startswith("0000") or "fail" in recipient.lower():
            self._status_store[msg_id] = DeliveryStatus.FAILED
            analysis = CommunicationFailureTranslator.translate(
                channel=channel,
                recipient=recipient,
                raw_error="Provider delivery failure: Recipient unreachable or invalid destination handset.",
            )
            return ProviderMessageResult(
                success=False,
                status=DeliveryStatus.FAILED,
                provider_name=self._provider_name,
                provider_message_id=msg_id,
                failure_category=analysis.category.value,
                error_message=analysis.recruiter_message,
                technical_details=analysis.technical_details,
            )

        self._status_store[msg_id] = DeliveryStatus.SENT
        return ProviderMessageResult(
            success=True,
            status=DeliveryStatus.SENT,
            provider_name=self._provider_name,
            provider_message_id=msg_id,
            error_message=None,
        )

    def check_status(self, provider_message_id: str) -> DeliveryStatus:
        return self._status_store.get(provider_message_id, DeliveryStatus.SENT)

    def health(self) -> dict:
        return {
            "id": "mock",
            "name": "Mock Gateway (Offline Dev)",
            "status": "operational",
            "detail": "In-memory mock provider — no external calls. Use dummy provider for full simulation.",
        }


class ProviderFactory:
    """
    Factory resolving CommunicationProvider instances (DIP & OCP).

    Provider resolution order:
    - 'dummy' (default): Standalone HTTP Dummy Communication Service (port 9000)
    - 'mock' / anything else: In-memory fallback (no external service required)

    WhatsApp and other real providers have been intentionally removed.
    All production and demo usage should use the dummy provider.
    """

    _providers: Dict[str, CommunicationProvider] = {}

    @classmethod
    def get_provider(cls, channel: str = "sms", provider_name: Optional[str] = None) -> CommunicationProvider:
        configured = provider_name or config("DEFAULT_COMMUNICATION_PROVIDER", default="dummy")

        # Dummy standalone HTTP provider (default)
        if configured in ("dummy", "dummy_service", "standalone", "auto"):
            key = "provider:dummy_service"
            if key not in cls._providers:
                cls._providers[key] = DummyServiceCommunicationProvider()
            return cls._providers[key]

        # Mock in-memory fallback
        key = f"mock:{channel}"
        if key not in cls._providers:
            cls._providers[key] = MockCommunicationProvider(provider_name=f"mock-{channel}")
        return cls._providers[key]

    @classmethod
    def register_provider(cls, name: str, provider: CommunicationProvider) -> None:
        """Register a custom provider instance (useful for testing)."""
        cls._providers[name] = provider

    @classmethod
    def catalog(cls) -> list:
        """Provider catalog returned by the health/providers API endpoint."""
        dummy = cls.get_provider(channel="sms", provider_name="dummy")
        return [
            {
                "id": "dummy",
                "name": "Dummy Communication Service",
                "description": (
                    "Standalone HTTP microservice simulating a real communication provider. "
                    "Supports send, status polling, webhook callbacks, and failure simulation modes."
                ),
                "channels": ["sms", "whatsapp", "email"],
                "health": dummy.health(),
            },
        ]

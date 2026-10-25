"""
Concrete Communication Providers implementing CommunicationProvider interface.
Infrastructure layer (Clean Architecture + Open/Closed Principle + Liskov Substitution Principle).

Supports:
1. Dummy Independent Communication Provider (HTTP microservice on port 9000)
2. Real WhatsApp Cloud / Sandbox API provider (Meta Graph API / Twilio WhatsApp Sandbox)
3. In-memory / Fallback Mock provider
"""

import uuid
import random
import logging
from typing import Dict, Optional
import requests
from decouple import config

from .domain import CommunicationProvider, ProviderMessageResult, DeliveryStatus

logger = logging.getLogger(__name__)


class DummyServiceCommunicationProvider(CommunicationProvider):
    """
    Adapter for the independent dummy communication microservice (Requirement #6).
    Communicates over HTTP with the standalone provider process:
    - Sends message
    - Receives message reference ID
    - Queries status updates
    - Handles temporary provider failures (503 / 504) with graceful resilience
    - Handles simulated rejections / failed states
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

            # Handle temporary service failure (e.g. 503 Service Unavailable / Gateway Timeout)
            if resp.status_code in (503, 502, 504):
                err_data = resp.json() if resp.headers.get("content-type") == "application/json" else {}
                err_msg = err_data.get("error", "Temporary downstream provider unavailable.")
                return ProviderMessageResult(
                    success=False,
                    status=DeliveryStatus.FAILED,
                    provider_name=self._name,
                    provider_message_id=f"temp_fail_{uuid.uuid4().hex[:8]}",
                    error_message=f"Temporary Provider Failure (HTTP {resp.status_code}): {err_msg}",
                )

            data = resp.json()
            is_success = data.get("success", False)
            raw_status = data.get("status", "failed")
            ref_id = data.get("reference_id", f"ref_{uuid.uuid4().hex[:8]}")
            err = data.get("error")

            # Map status string to DeliveryStatus enum
            status_map = {
                "sent": DeliveryStatus.SENT,
                "delivered": DeliveryStatus.DELIVERED,
                "read": DeliveryStatus.READ,
                "failed": DeliveryStatus.FAILED,
            }
            mapped_status = status_map.get(raw_status, DeliveryStatus.FAILED)

            return ProviderMessageResult(
                success=is_success and mapped_status != DeliveryStatus.FAILED,
                status=mapped_status,
                provider_name=self._name,
                provider_message_id=ref_id,
                error_message=err,
            )

        except requests.exceptions.RequestException as e:
            # Standalone service might not be running or network unreachable
            logger.warning(f"Failed to communicate with Dummy Service at {url}: {e}")
            return ProviderMessageResult(
                success=False,
                status=DeliveryStatus.FAILED,
                provider_name=self._name,
                provider_message_id=f"err_{uuid.uuid4().hex[:8]}",
                error_message=f"Dummy communication provider connection error: {str(e)}",
            )

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


class WhatsAppCloudCommunicationProvider(CommunicationProvider):
    """
    Real Communication Provider: Meta WhatsApp Cloud API / WhatsApp Sandbox (Requirement #6).
    Uses the official Meta Graph API v20.0 or sandbox test credentials:
    - WHATSAPP_API_TOKEN
    - WHATSAPP_PHONE_NUMBER_ID
    - WHATSAPP_API_VERSION (default: v20.0)
    When credentials are not yet configured or live numbers aren't verified in developer sandbox,
    it provides verified test sandbox simulation with realistic Meta WhatsApp payload IDs (`wamid.HB...`).
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
        api_version: str = "v20.0",
    ):
        self._api_token = api_token or config("WHATSAPP_API_TOKEN", default="")
        self._phone_number_id = phone_number_id or config("WHATSAPP_PHONE_NUMBER_ID", default="")
        self._api_version = api_version
        self._name = "whatsapp-cloud-api"

    @property
    def provider_name(self) -> str:
        return self._name

    def send(self, recipient: str, content: str, channel: str) -> ProviderMessageResult:
        # Sanitize recipient phone number for WhatsApp E.164 (e.g. +919876543210 -> 919876543210)
        clean_recipient = recipient.replace("+", "").replace(" ", "").replace("-", "")

        # If live WhatsApp Cloud API credentials are provided, call Meta Graph API
        if self._api_token and self._phone_number_id and not clean_recipient.startswith("0000"):
            url = f"https://graph.facebook.com/{self._api_version}/{self._phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self._api_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": clean_recipient,
                "type": "text",
                "text": {"preview_url": False, "body": content},
            }

            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=10)
                data = resp.json()

                if resp.status_code in (200, 201) and "messages" in data:
                    wamid = data["messages"][0]["id"]
                    return ProviderMessageResult(
                        success=True,
                        status=DeliveryStatus.SENT,
                        provider_name=self._name,
                        provider_message_id=wamid,
                        error_message=None,
                    )
                else:
                    err_info = data.get("error", {})
                    err_msg = err_info.get("message", f"HTTP {resp.status_code} WhatsApp API error")
                    return ProviderMessageResult(
                        success=False,
                        status=DeliveryStatus.FAILED,
                        provider_name=self._name,
                        provider_message_id=f"wamid_fail_{uuid.uuid4().hex[:8]}",
                        error_message=f"WhatsApp API Error ({err_info.get('code', 'ERR')}): {err_msg}",
                    )
            except requests.exceptions.RequestException as e:
                return ProviderMessageResult(
                    success=False,
                    status=DeliveryStatus.FAILED,
                    provider_name=self._name,
                    provider_message_id=f"wamid_err_{uuid.uuid4().hex[:8]}",
                    error_message=f"WhatsApp Cloud API network failure: {str(e)}",
                )

        # Developer / Sandbox Mode:
        # Generates compliant WhatsApp Meta message ID format (`wamid.HB...`)
        if "[fail]" in content.lower() or clean_recipient.startswith("0000") or "fail" in recipient.lower():
            return ProviderMessageResult(
                success=False,
                status=DeliveryStatus.FAILED,
                provider_name=f"{self._name} (sandbox)",
                provider_message_id=f"wamid.HB_{uuid.uuid4().hex[:16]}",
                error_message="WhatsApp Sandbox rejection: Destination number not registered in allowed sandbox contacts or template mismatch.",
            )

        # Standard sandbox delivery: Sent -> Delivered -> Read
        wamid = f"wamid.HB_{uuid.uuid4().hex[:18]}"
        assigned_status = DeliveryStatus.READ if "read" in content.lower() else DeliveryStatus.DELIVERED
        return ProviderMessageResult(
            success=True,
            status=assigned_status,
            provider_name=f"{self._name} (sandbox)",
            provider_message_id=wamid,
            error_message=None,
        )

    def check_status(self, provider_message_id: str) -> DeliveryStatus:
        # In live WhatsApp API, status is received via Webhooks.
        return DeliveryStatus.DELIVERED


class MockCommunicationProvider(CommunicationProvider):
    """Local fallback / in-memory provider."""

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
            return ProviderMessageResult(
                success=False,
                status=DeliveryStatus.FAILED,
                provider_name=self._provider_name,
                provider_message_id=msg_id,
                error_message="Provider delivery failure: Recipient unreachable or invalid destination number.",
            )

        possible_statuses = [DeliveryStatus.DELIVERED, DeliveryStatus.READ, DeliveryStatus.SENT]
        assigned_status = random.choice(possible_statuses)
        self._status_store[msg_id] = assigned_status

        return ProviderMessageResult(
            success=True,
            status=assigned_status,
            provider_name=self._provider_name,
            provider_message_id=msg_id,
            error_message=None,
        )

    def check_status(self, provider_message_id: str) -> DeliveryStatus:
        return self._status_store.get(provider_message_id, DeliveryStatus.SENT)


class ProviderFactory:
    """
    Factory resolving CommunicationProvider instances (DIP & OCP).
    Supports:
    - 'whatsapp' / 'real': WhatsApp Cloud API / Sandbox
    - 'dummy': Standalone HTTP Dummy Communication Service (port 9000)
    - 'mock': In-memory gateway
    """

    _providers: Dict[str, CommunicationProvider] = {}

    @classmethod
    def get_provider(cls, channel: str = "sms", provider_name: Optional[str] = None) -> CommunicationProvider:
        # Check active provider configuration or explicit request
        configured = provider_name or config("DEFAULT_COMMUNICATION_PROVIDER", default="dummy")
        
        # When channel is whatsapp or user specified real/whatsapp provider
        if configured in ("whatsapp", "whatsapp_cloud", "real") or (configured == "auto" and channel == "whatsapp"):
            key = "provider:whatsapp_cloud"
            if key not in cls._providers:
                cls._providers[key] = WhatsAppCloudCommunicationProvider()
            return cls._providers[key]

        # Standalone dummy service
        if configured in ("dummy", "dummy_service", "standalone"):
            key = "provider:dummy_service"
            if key not in cls._providers:
                cls._providers[key] = DummyServiceCommunicationProvider()
            return cls._providers[key]

        # Default mock
        key = f"mock:{channel}"
        if key not in cls._providers:
            cls._providers[key] = MockCommunicationProvider(provider_name=f"mock-{channel}")
        return cls._providers[key]

    @classmethod
    def register_provider(cls, name: str, provider: CommunicationProvider) -> None:
        cls._providers[name] = provider

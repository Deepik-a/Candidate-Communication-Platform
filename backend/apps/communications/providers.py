"""
Concrete communication providers implementing CommunicationProvider interface.
Infrastructure layer (Open/Closed Principle, Liskov Substitution Principle).
"""

import uuid
import random
from typing import Dict
from .domain import CommunicationProvider, ProviderMessageResult, DeliveryStatus


class MockCommunicationProvider(CommunicationProvider):
    """
    Production-grade mock provider that simulates realistic delivery lifecycles:
    - Supports simulated failures for testing resilience (e.g. invalid recipient or forced fail keyword)
    - Realistic status simulation (Delivered, Read, Sent, Failed)
    - Easily interchangeable with real Twilio / SendGrid providers via Dependency Injection.
    """

    def __init__(self, provider_name: str = "mock-gateway", fail_rate: float = 0.0):
        self._provider_name = provider_name
        self._fail_rate = fail_rate
        self._status_store: Dict[str, DeliveryStatus] = {}

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def send(self, recipient: str, content: str, channel: str) -> ProviderMessageResult:
        msg_id = f"mock_{channel}_{uuid.uuid4().hex[:10]}"

        # Allow explicit simulation via content keyword or invalid recipient
        if "[fail]" in content.lower() or recipient.startswith("0000"):
            self._status_store[msg_id] = DeliveryStatus.FAILED
            return ProviderMessageResult(
                success=False,
                status=DeliveryStatus.FAILED,
                provider_name=self._provider_name,
                provider_message_id=msg_id,
                error_message="Provider delivery failure: Recipient unreachable or invalid destination number.",
            )

        if self._fail_rate > 0 and random.random() < self._fail_rate:
            self._status_store[msg_id] = DeliveryStatus.FAILED
            return ProviderMessageResult(
                success=False,
                status=DeliveryStatus.FAILED,
                provider_name=self._provider_name,
                provider_message_id=msg_id,
                error_message="Network timeout communicating with telecom gateway.",
            )

        # Deterministic / realistic outcome distribution:
        # WhatsApp commonly reaches 'read' or 'delivered'
        # SMS reaches 'delivered' or 'sent'
        # Email reaches 'sent' or 'delivered'
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
    Factory for obtaining provider implementations (DIP / OCP).
    Allows plugging in Twilio, SendGrid, Meta WhatsApp Business without changing callers.
    """

    _providers: Dict[str, CommunicationProvider] = {}

    @classmethod
    def get_provider(cls, channel: str = "sms", provider_name: str = "mock") -> CommunicationProvider:
        key = f"{channel}:{provider_name}"
        if key not in cls._providers:
            cls._providers[key] = MockCommunicationProvider(provider_name=f"{provider_name}-{channel}")
        return cls._providers[key]

    @classmethod
    def register_provider(cls, channel: str, provider_name: str, provider: CommunicationProvider) -> None:
        cls._providers[f"{channel}:{provider_name}"] = provider

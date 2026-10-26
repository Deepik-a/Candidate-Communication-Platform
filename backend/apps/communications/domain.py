"""
Communications Domain - Entities, Value Objects, and Provider Interfaces.
Framework-agnostic domain layer (Clean Architecture + SOLID).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ProviderType(str, Enum):
    MOCK = "mock"
    TWILIO = "twilio"
    WHATSAPP_BUSINESS = "whatsapp_business"
    SENDGRID = "sendgrid"


class DeliveryStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


@dataclass(frozen=True)
class ProviderMessageResult:
    """Immutable result object returned by a communication provider."""
    success: bool
    status: DeliveryStatus
    provider_name: str
    provider_message_id: str
    error_message: Optional[str] = None


class CommunicationProvider(ABC):
    """
    Abstract interface for all communication providers (ISP & DIP).
    Any SMS, WhatsApp, Email or mock provider implements this interface.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name/identifier of the provider."""
        ...

    @abstractmethod
    def send(self, recipient: str, content: str, channel: str) -> ProviderMessageResult:
        """Send message through provider and return standardized delivery status."""
        ...

    @abstractmethod
    def check_status(self, provider_message_id: str) -> DeliveryStatus:
        """Fetch latest status from provider."""
        ...

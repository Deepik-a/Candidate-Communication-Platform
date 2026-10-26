"""
Tests for Candidate Management and Communication flows.
Verifying SOLID principles & Clean Architecture behaviors.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase
from apps.candidates.infrastructure.models import Candidate, MessageStatus
from apps.communications.models import Message, MessageStatusLog
from apps.communications.services import CommunicationService
from apps.communications.domain import CommunicationProvider, ProviderMessageResult, DeliveryStatus
from apps.communications.providers import (
    DummyServiceCommunicationProvider,
    WhatsAppCloudCommunicationProvider,
    ProviderFactory,
)


class StubFailProvider(CommunicationProvider):
    """Test provider that simulates selective failure (LSP)."""

    @property
    def provider_name(self) -> str:
        return "stub-fail-provider"

    def send(self, recipient: str, content: str, channel: str) -> ProviderMessageResult:
        if "fail" in recipient.lower():
            return ProviderMessageResult(
                success=False,
                status=DeliveryStatus.FAILED,
                provider_name=self.provider_name,
                provider_message_id="fail_id_123",
                error_message="Simulated gateway error for recipient",
            )
        return ProviderMessageResult(
            success=True,
            status=DeliveryStatus.DELIVERED,
            provider_name=self.provider_name,
            provider_message_id="success_id_123",
            error_message=None,
        )

    def check_status(self, provider_message_id: str) -> DeliveryStatus:
        return DeliveryStatus.DELIVERED


class CandidateCommunicationTests(TestCase):
    def setUp(self):
        self.c1 = Candidate.objects.create(
            full_name="Rahul Sharma",
            mobile_number="+919876543210",
            email="rahul@example.com",
        )
        self.c2 = Candidate.objects.create(
            full_name="Priya Shah",
            mobile_number="+919876543211",
            email="priya@example.com",
        )
        self.c3 = Candidate.objects.create(
            full_name="Amit Kumar",
            mobile_number="fail_number_999",
            email="amit@example.com",
        )

    def test_single_message_flow(self):
        service = CommunicationService(provider=StubFailProvider())
        outcome = service.send_single_message(
            candidate_id=self.c1.id,
            channel="sms",
            content="Hello Rahul, your interview is scheduled.",
        )
        self.assertTrue(outcome.success)
        self.assertEqual(outcome.status, "delivered")

        self.c1.refresh_from_db()
        self.assertIsNotNone(self.c1.last_message_date)
        self.assertEqual(self.c1.status, MessageStatus.DELIVERED)

        messages = Message.objects.filter(candidate=self.c1)
        self.assertEqual(messages.count(), 1)
        self.assertEqual(messages.first().status, MessageStatusLog.DELIVERED)

    def test_bulk_messaging_independent_tracking(self):
        """
        Requirement #4:
        One candidate's failure should not prevent remaining messages from being processed.
        Clearly show individual result for each candidate.
        """
        service = CommunicationService(provider=StubFailProvider())
        result = service.send_bulk_messages(
            candidate_ids=[self.c1.id, self.c2.id, self.c3.id],
            channel="whatsapp",
            content="Your interview is scheduled for tomorrow.",
        )

        self.assertEqual(result.total_requested, 3)
        self.assertEqual(result.successful_count, 2)
        self.assertEqual(result.failed_count, 1)

        # Candidate 1 and 2 succeeded
        self.assertTrue(result.outcomes[0].success)
        self.assertEqual(result.outcomes[0].candidate_name, "Rahul Sharma")
        self.assertTrue(result.outcomes[1].success)
        self.assertEqual(result.outcomes[1].candidate_name, "Priya Shah")

        # Candidate 3 failed independently without crashing the others
        self.assertFalse(result.outcomes[2].success)
        self.assertEqual(result.outcomes[2].candidate_name, "Amit Kumar")
        self.assertEqual(result.outcomes[2].status, "failed")

        # Check DB states
        self.c1.refresh_from_db()
        self.assertEqual(self.c1.status, MessageStatus.DELIVERED)
        self.c3.refresh_from_db()
        self.assertEqual(self.c3.status, MessageStatus.FAILED)

    def test_dummy_provider_integration(self):
        """Requirement #6: Dummy independent communication provider."""
        provider = DummyServiceCommunicationProvider(base_url="http://localhost:9000")
        
        # Test success against running dummy service
        res = provider.send(self.c1.mobile_number, "Test interview notification", "sms")
        self.assertTrue(res.success)
        self.assertTrue(res.provider_message_id.startswith("dummy_sms_"))
        self.assertIn(res.status, [DeliveryStatus.SENT, DeliveryStatus.DELIVERED])

        # Test simulated failure
        fail_res = provider.send(self.c1.mobile_number, "Test [fail]", "sms")
        self.assertFalse(fail_res.success)
        self.assertEqual(fail_res.status, DeliveryStatus.FAILED)
        self.assertIsNotNone(fail_res.error_message)

    def test_whatsapp_cloud_provider_integration(self):
        """Requirement #6: Real WhatsApp API / WhatsApp Sandbox provider."""
        provider = WhatsAppCloudCommunicationProvider()
        
        # Test WhatsApp sandbox delivery
        res = provider.send(self.c1.mobile_number, "Welcome to the recruitment process", "whatsapp")
        self.assertTrue(res.success)
        self.assertTrue(res.provider_message_id.startswith("wamid.HB"))
        self.assertIn(res.status, [DeliveryStatus.SENT, DeliveryStatus.DELIVERED, DeliveryStatus.READ])

        # Test WhatsApp sandbox simulated failure
        fail_res = provider.send("0000000000", "Welcome [fail]", "whatsapp")
        self.assertFalse(fail_res.success)
        self.assertEqual(fail_res.status, DeliveryStatus.FAILED)
        self.assertIn("Sandbox rejection", fail_res.error_message)

    def test_provider_factory_resolution(self):
        """Test provider factory can resolve both dummy and whatsapp providers."""
        dummy_p = ProviderFactory.get_provider(channel="sms", provider_name="dummy")
        self.assertIsInstance(dummy_p, DummyServiceCommunicationProvider)

        wa_p = ProviderFactory.get_provider(channel="whatsapp", provider_name="whatsapp")
        self.assertIsInstance(wa_p, WhatsAppCloudCommunicationProvider)

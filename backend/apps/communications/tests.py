"""
Tests for Candidate Management and Communication flows.
Verifying Requirements #7 (Message Status Updates & Idempotency),
#8 (Communication Failure Translation & Recruiter Messages),
and #10 (Candidate Communication History).
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from apps.candidates.infrastructure.models import Candidate, MessageStatus
from apps.communications.models import Message, MessageStatusLog
from apps.communications.services import CommunicationService, STATUS_PRECEDENCE
from apps.communications.failures import CommunicationFailureTranslator, FailureCategory
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
            analysis = CommunicationFailureTranslator.translate(
                channel=channel,
                recipient=recipient,
                raw_error="Simulated carrier delivery failure: Recipient unreachable.",
            )
            return ProviderMessageResult(
                success=False,
                status=DeliveryStatus.FAILED,
                provider_name=self.provider_name,
                provider_message_id="fail_id_123",
                failure_category=analysis.category.value,
                error_message=analysis.recruiter_message,
                technical_details=analysis.technical_details,
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
        self.client = APIClient()
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

    # ── Requirement #7: Message Status Updates & Idempotency ────────────────────

    def test_message_status_progression_sent_delivered_read(self):
        """
        Requirement #7: Message status progression
        Message Sent -> Sent -> Delivered -> Read
        """
        service = CommunicationService(provider=StubFailProvider())
        outcome = service.send_single_message(
            candidate_id=self.c1.id,
            channel="sms",
            content="Hello Rahul, your interview is scheduled.",
            forced_status="sent",
        )
        message_id = outcome.message_id
        self.assertIsNotNone(message_id)

        # 1. Initially Sent
        msg = Message.objects.get(id=message_id)
        self.assertEqual(msg.status, MessageStatusLog.SENT)
        self.c1.refresh_from_db()
        self.assertEqual(self.c1.status, MessageStatus.SENT)

        # 2. Transition: Sent -> Delivered
        outcome_deliv = service.update_message_status(message_id=message_id, new_status="delivered")
        self.assertTrue(outcome_deliv.updated)
        self.assertFalse(outcome_deliv.was_duplicate)
        msg.refresh_from_db()
        self.assertEqual(msg.status, MessageStatusLog.DELIVERED)
        self.c1.refresh_from_db()
        self.assertEqual(self.c1.status, MessageStatus.DELIVERED)

        # 3. Transition: Delivered -> Read
        outcome_read = service.update_message_status(message_id=message_id, new_status="read")
        self.assertTrue(outcome_read.updated)
        self.assertFalse(outcome_read.was_duplicate)
        msg.refresh_from_db()
        self.assertEqual(msg.status, MessageStatusLog.READ)
        self.c1.refresh_from_db()
        self.assertEqual(self.c1.status, MessageStatus.READ)

    def test_status_update_idempotency_duplicate_calls(self):
        """
        Requirement #7: The platform should behave correctly if the same update is received more than once.
        """
        service = CommunicationService(provider=StubFailProvider())
        outcome = service.send_single_message(
            candidate_id=self.c1.id,
            channel="whatsapp",
            content="Interview details",
            forced_status="sent",
        )
        msg_id = outcome.message_id

        # First update to delivered
        res1 = service.update_message_status(message_id=msg_id, new_status="delivered")
        self.assertTrue(res1.updated)
        self.assertFalse(res1.was_duplicate)

        # Duplicate update with the EXACT SAME status
        res2 = service.update_message_status(message_id=msg_id, new_status="delivered")
        self.assertFalse(res2.updated)
        self.assertTrue(res2.was_duplicate)
        self.assertIn("already in 'delivered' status", res2.detail)

        # Verify database message is unchanged and healthy
        msg = Message.objects.get(id=msg_id)
        self.assertEqual(msg.status, MessageStatusLog.DELIVERED)

    def test_status_update_anti_regression_out_of_order(self):
        """
        Requirement #7: An out-of-order callback (e.g. Sent arriving after Delivered)
        should NOT regress status back.
        """
        service = CommunicationService(provider=StubFailProvider())
        outcome = service.send_single_message(
            candidate_id=self.c1.id,
            channel="whatsapp",
            content="Reminder",
            forced_status="read",
        )
        msg_id = outcome.message_id

        # Attempt to downgrade to 'delivered' or 'sent'
        res = service.update_message_status(message_id=msg_id, new_status="delivered")
        self.assertFalse(res.updated)
        self.assertFalse(res.was_duplicate)
        self.assertIn("higher precedence", res.detail)

        msg = Message.objects.get(id=msg_id)
        self.assertEqual(msg.status, MessageStatusLog.READ)

    def test_webhook_endpoint_idempotent_processing(self):
        """Requirement #7: POST /api/v1/communications/webhook/ receives callbacks idempotently."""
        msg = Message.objects.create(
            candidate=self.c1,
            channel="whatsapp",
            content="Test webhook notification",
            status="sent",
            provider="dummy-service",
            provider_message_id="dummy_ref_xyz123",
        )

        # 1. Send delivered callback via webhook
        resp1 = self.client.post(
            "/api/v1/communications/webhook/",
            data={"reference_id": "dummy_ref_xyz123", "status": "delivered"},
            format="json",
        )
        self.assertEqual(resp1.status_code, 200)
        self.assertTrue(resp1.data["success"])
        self.assertFalse(resp1.data["was_duplicate"])

        # 2. Send duplicate delivered callback
        resp2 = self.client.post(
            "/api/v1/communications/webhook/",
            data={"reference_id": "dummy_ref_xyz123", "status": "delivered"},
            format="json",
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertTrue(resp2.data["success"])
        self.assertTrue(resp2.data["was_duplicate"])

    # ── Requirement #8: Handling Communication Failures ─────────────────────────

    def test_failure_translation_invalid_recipient(self):
        """Requirement #8: Invalid recipient returns meaningful message instead of technical error."""
        analysis = CommunicationFailureTranslator.translate(
            channel="sms",
            recipient="not-a-phone",
            raw_error="Carrier validation rejected",
        )
        self.assertEqual(analysis.category, FailureCategory.INVALID_RECIPIENT)
        self.assertIn("Invalid recipient contact", analysis.recruiter_message)
        self.assertFalse(analysis.is_retryable)

    def test_failure_translation_rate_limiting(self):
        """Requirement #8: Rate limiting returns clear recruiter guidance."""
        analysis = CommunicationFailureTranslator.translate(
            channel="sms",
            recipient="+919876543210",
            status_code=429,
            raw_error="HTTP 429 Too Many Requests in window",
        )
        self.assertEqual(analysis.category, FailureCategory.RATE_LIMIT_EXCEEDED)
        self.assertIn("Sending limit reached", analysis.recruiter_message)
        self.assertTrue(analysis.is_retryable)

    def test_failure_translation_temporary_provider_failure(self):
        """Requirement #8: Temporary provider failure (503) informs recruiter it can be retried."""
        analysis = CommunicationFailureTranslator.translate(
            channel="whatsapp",
            recipient="+919876543210",
            status_code=503,
            raw_error="503 Service Unavailable downstream network",
        )
        self.assertEqual(analysis.category, FailureCategory.TEMPORARY_PROVIDER_FAILURE)
        self.assertIn("Temporary provider delay", analysis.recruiter_message)
        self.assertTrue(analysis.is_retryable)

    def test_failure_translation_delivery_failure(self):
        """Requirement #8: Delivery failure explains carrier/handset reasons."""
        analysis = CommunicationFailureTranslator.translate(
            channel="sms",
            recipient="+919876543210",
            raw_error="Carrier rejected: handset out of coverage or unreachable subscriber.",
        )
        self.assertEqual(analysis.category, FailureCategory.DELIVERY_FAILURE)
        self.assertIn("Delivery failed: The candidate's mobile carrier could not deliver", analysis.recruiter_message)

    def test_failure_translation_service_unavailable(self):
        """Requirement #8: Connection error returns clean service unavailable explanation."""
        analysis = CommunicationFailureTranslator.translate(
            channel="sms",
            recipient="+919876543210",
            raw_error="Connection refused by remote host (WinError 10061)",
        )
        self.assertEqual(analysis.category, FailureCategory.SERVICE_UNAVAILABLE)
        self.assertIn("Communication service unavailable", analysis.recruiter_message)

    def test_single_message_handles_invalid_recipient_gracefully(self):
        """Service should record meaningful failure when candidate has invalid contact number."""
        c_bad = Candidate.objects.create(
            full_name="Bad Phone Candidate",
            mobile_number="abc",
            email=None,
        )
        service = CommunicationService(provider=StubFailProvider())
        outcome = service.send_single_message(
            candidate_id=c_bad.id,
            channel="sms",
            content="Hello",
        )
        self.assertFalse(outcome.success)
        self.assertEqual(outcome.status, "failed")
        self.assertEqual(outcome.failure_category, "invalid_recipient")
        self.assertIn("Invalid recipient contact", outcome.error_message)

    # ── Requirement #10: Communication History ──────────────────────────────────

    def test_candidate_communication_history_endpoint(self):
        """
        Requirement #10: Recruiters can view communication history of candidate:
        What was sent, when it was sent, current status, whether it failed, and why it failed.
        """
        # Create successful message
        m1 = Message.objects.create(
            candidate=self.c1,
            channel="sms",
            content="Welcome to our hiring process.",
            status="read",
            provider="dummy-service",
            provider_message_id="dummy_01",
        )
        # Create delivered message
        m2 = Message.objects.create(
            candidate=self.c1,
            channel="sms",
            content="Hello Rahul, your interview is scheduled for tomorrow at 11:00 AM.",
            status="delivered",
            provider="dummy-service",
            provider_message_id="dummy_02",
        )
        # Create failed message with why it failed
        m3 = Message.objects.create(
            candidate=self.c1,
            channel="whatsapp",
            content="Urgent: Please share your portfolio.",
            status="failed",
            provider="whatsapp-cloud-api",
            provider_message_id="wamid_fail_03",
            failure_category="temporary_provider_failure",
            error_message="Temporary provider delay: The downstream telecommunication network experienced a momentary interruption.",
        )

        resp = self.client.get(f"/api/v1/communications/candidate/{self.c1.id}/")
        self.assertEqual(resp.status_code, 200)
        messages = resp.data
        self.assertEqual(len(messages), 3)

        # Most recent first
        latest = messages[0]
        self.assertEqual(latest["id"], m3.id)
        self.assertEqual(latest["channel"], "whatsapp")
        self.assertEqual(latest["content"], "Urgent: Please share your portfolio.")
        self.assertEqual(latest["status"], "failed")
        self.assertEqual(latest["failure_category"], "temporary_provider_failure")
        self.assertIn("Temporary provider delay", latest["error_message"])

        # Check candidate details are included
        self.assertEqual(latest["candidate_name"], "Rahul Sharma")
        self.assertEqual(latest["candidate_phone"], "+919876543210")

"""
Communications API Views.
Presentation Layer adhering to Single Responsibility and Clean Architecture.
Endpoints for:
- Sending individual message
- Sending bulk messages with independent per-candidate tracking
- Candidate message history
- Message status retrieval & manual updates
- Provider sync
- Provider Webhook Receiver with idempotent status progression (Requirement #7)
"""

import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema

from apps.candidates.infrastructure.models import Candidate
from .models import Message
from .services import CommunicationService
from .serializers import (
    MessageSerializer,
    SendMessageSerializer,
    BulkSendMessageSerializer,
    BulkMessageResponseSerializer,
    CandidateMessageOutcomeSerializer,
    UpdateMessageStatusSerializer,
    WebhookStatusUpdateSerializer,
)


def get_communication_service() -> CommunicationService:
    """Dependency injection factory for CommunicationService."""
    return CommunicationService()


class SendMessageView(APIView):
    """
    POST /api/v1/communications/send/
    Sends a message to an individual candidate through a communication provider.
    Records communication and updates candidate journey status.
    """

    @extend_schema(
        request=SendMessageSerializer,
        responses={201: CandidateMessageOutcomeSerializer},
        summary='Send message to an individual candidate',
    )
    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        service = get_communication_service()
        outcome = service.send_single_message(
            candidate_id=serializer.validated_data['candidate_id'],
            channel=serializer.validated_data['channel'],
            content=serializer.validated_data['content'],
            provider_name=serializer.validated_data.get('provider') or None,
        )

        resp_status = status.HTTP_201_CREATED if outcome.success else status.HTTP_200_OK
        return Response(CandidateMessageOutcomeSerializer(outcome).data, status=resp_status)


class BulkSendMessageView(APIView):
    """
    POST /api/v1/communications/bulk-send/
    Sends the same message to multiple selected candidates.
    Each candidate's message is tracked independently.
    One candidate's failure does not prevent remaining messages from being processed.
    """

    @extend_schema(
        request=BulkSendMessageSerializer,
        responses={200: BulkMessageResponseSerializer},
        summary='Send bulk messages to multiple candidates',
    )
    def post(self, request):
        serializer = BulkSendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        service = get_communication_service()
        bulk_result = service.send_bulk_messages(
            candidate_ids=serializer.validated_data['candidate_ids'],
            channel=serializer.validated_data['channel'],
            content=serializer.validated_data['content'],
            provider_name=serializer.validated_data.get('provider') or None,
        )

        return Response(BulkMessageResponseSerializer(bulk_result).data, status=status.HTTP_200_OK)


class CandidateMessagesView(APIView):
    """
    GET /api/v1/communications/candidate/<candidate_id>/
    Requirement #10: Candidate communication history.
    Provides detailed timeline of messages sent to a specific candidate,
    including content, channel, status, timestamp, and failure details.
    """

    @extend_schema(
        responses={200: MessageSerializer(many=True)},
        summary='Get message history for a candidate',
    )
    def get(self, request, candidate_id):
        try:
            candidate = Candidate.objects.get(id=candidate_id)
        except Candidate.DoesNotExist:
            return Response({'detail': 'Candidate not found.'}, status=status.HTTP_404_NOT_FOUND)

        messages = Message.objects.filter(candidate=candidate).order_by('-sent_at', '-id')
        return Response(MessageSerializer(messages, many=True).data)


class MessageDetailStatusView(APIView):
    """
    GET   /api/v1/communications/messages/<message_id>/ — get message details & status
    PATCH /api/v1/communications/messages/<message_id>/ — update message status (recruiter simulation / manual update)
    """

    @extend_schema(
        responses={200: MessageSerializer},
        summary='Get message status and details',
    )
    def get(self, request, message_id):
        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return Response({'detail': 'Message not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(MessageSerializer(message).data)

    @extend_schema(
        request=UpdateMessageStatusSerializer,
        responses={200: MessageSerializer},
        summary='Update message status',
    )
    def patch(self, request, message_id):
        serializer = UpdateMessageStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        service = get_communication_service()
        outcome = service.update_message_status(
            message_id=message_id,
            new_status=serializer.validated_data['status'],
            raw_error=serializer.validated_data.get('error') or None,
        )
        if not outcome.message:
            return Response({'detail': outcome.detail}, status=status.HTTP_404_NOT_FOUND)

        data = MessageSerializer(outcome.message).data
        data['was_duplicate'] = outcome.was_duplicate
        data['update_detail'] = outcome.detail
        return Response(data, status=status.HTTP_200_OK)


class MessageSyncStatusView(APIView):
    """
    POST /api/v1/communications/messages/<message_id>/sync/
    Actively queries the downstream provider for the latest status and updates database.
    """

    @extend_schema(
        responses={200: MessageSerializer},
        summary='Sync latest status directly from external provider',
    )
    def post(self, request, message_id):
        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return Response({'detail': 'Message not found.'}, status=status.HTTP_404_NOT_FOUND)

        service = get_communication_service()
        if message.provider_message_id:
            from .providers import ProviderFactory
            provider_type = "whatsapp" if "wamid" in message.provider_message_id else "dummy"
            provider = ProviderFactory.get_provider(channel=message.channel, provider_name=provider_type)
            latest_status = provider.check_status(message.provider_message_id)

            outcome = service.update_message_status(
                message_id=message.id,
                new_status=latest_status.value,
            )
            message = outcome.message or message

        return Response(MessageSerializer(message).data)


class ProviderWebhookView(APIView):
    """
    POST /api/v1/communications/webhook/
    Requirement #7: Universal provider callback/webhook receiver.
    Receives status updates from communication providers (Dummy Service, WhatsApp Cloud API, Twilio).
    Features:
    - Automatically maps provider-specific payloads (reference_id, wamid, MessageSid)
    - Enforces progression: Sent -> Delivered -> Read
    - Idempotent: Handles repeated callbacks gracefully with HTTP 200 without duplicate actions
    - Synchronizes Candidate journey status in real-time
    """

    @extend_schema(
        summary='Universal provider webhook receiver',
        responses={200: dict},
    )
    def post(self, request):
        payload = request.data or {}
        
        # 1. Parse provider message reference ID & target status
        provider_msg_id = None
        target_status = None
        raw_error = None

        # Format A: Meta WhatsApp Cloud API Webhook structure
        # { "entry": [ { "changes": [ { "value": { "statuses": [ { "id": "wamid...", "status": "delivered" } ] } } ] } ] }
        if "entry" in payload and isinstance(payload.get("entry"), list):
            try:
                entry = payload["entry"][0]
                changes = entry.get("changes", [])[0]
                val = changes.get("value", {})
                statuses = val.get("statuses", [])
                if statuses:
                    s_item = statuses[0]
                    provider_msg_id = s_item.get("id")
                    target_status = s_item.get("status")
                    if s_item.get("errors"):
                        raw_error = json.dumps(s_item.get("errors"))
            except (IndexError, KeyError, TypeError):
                pass

        # Format B: Twilio format (MessageSid, MessageStatus)
        if not provider_msg_id and ("MessageSid" in payload or "MessageStatus" in payload):
            provider_msg_id = payload.get("MessageSid")
            target_status = payload.get("MessageStatus")
            raw_error = payload.get("ErrorMessage")

        # Format C: Dummy Service or standard generic webhook
        if not provider_msg_id:
            provider_msg_id = (
                payload.get("provider_message_id")
                or payload.get("reference_id")
                or payload.get("message_ref")
                or payload.get("id")
            )
            target_status = payload.get("status")
            raw_error = payload.get("error") or payload.get("error_message")

        # Direct message_id fallback if provider_message_id is not known
        direct_msg_id = payload.get("message_id")

        if not target_status:
            return Response(
                {"error": "Missing 'status' in webhook payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not provider_msg_id and not direct_msg_id:
            return Response(
                {"error": "Missing 'provider_message_id', 'reference_id', or 'message_id' in webhook payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = get_communication_service()
        outcome = service.update_message_status(
            message_id=int(direct_msg_id) if direct_msg_id else None,
            provider_message_id=str(provider_msg_id) if provider_msg_id else None,
            new_status=target_status,
            raw_error=raw_error,
        )

        if not outcome.message:
            return Response(
                {"success": False, "detail": outcome.detail},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "success": True,
                "message_id": outcome.message.id,
                "provider_message_id": outcome.message.provider_message_id,
                "status": outcome.status,
                "was_duplicate": outcome.was_duplicate,
                "detail": outcome.detail,
            },
            status=status.HTTP_200_OK,
        )

    def get(self, request):
        """Supports webhook subscription verification (e.g. WhatsApp / Meta webhook challenge)."""
        hub_mode = request.GET.get("hub.mode")
        hub_challenge = request.GET.get("hub.challenge")
        hub_verify_token = request.GET.get("hub.verify_token")

        if hub_mode == "subscribe" and hub_challenge:
            return Response(int(hub_challenge), status=status.HTTP_200_OK)
        return Response({"status": "active", "service": "communication-webhook-listener"}, status=status.HTTP_200_OK)

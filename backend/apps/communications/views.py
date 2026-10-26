"""
Communications API Views.
Presentation Layer adhering to Single Responsibility and Clean Architecture.
Endpoints for:
- Sending individual message
- Sending bulk messages with independent per-candidate tracking
- Candidate message history
- Message status retrieval & updates (provider callbacks / manual sync)
"""

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
    """GET /api/v1/communications/candidate/<candidate_id>/ — message history."""

    @extend_schema(
        responses={200: MessageSerializer(many=True)},
        summary='Get message history for a candidate',
    )
    def get(self, request, candidate_id):
        try:
            candidate = Candidate.objects.get(id=candidate_id)
        except Candidate.DoesNotExist:
            return Response({'detail': 'Candidate not found.'}, status=status.HTTP_404_NOT_FOUND)

        messages = Message.objects.filter(candidate=candidate).order_by('-sent_at')
        return Response(MessageSerializer(messages, many=True).data)


class MessageDetailStatusView(APIView):
    """
    GET   /api/v1/communications/messages/<message_id>/ — get message details & status
    PATCH /api/v1/communications/messages/<message_id>/ — update message status (from provider webhook or sync)
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
        updated_message = service.update_message_status(
            message_id=message_id,
            new_status=serializer.validated_data['status'],
        )
        if not updated_message:
            return Response({'detail': 'Message not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(MessageSerializer(updated_message).data)

    @extend_schema(
        responses={200: MessageSerializer},
        summary='Sync latest status directly from external provider',
    )
    def post(self, request, message_id):
        """Syncs the latest status from the external communication provider."""
        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return Response({'detail': 'Message not found.'}, status=status.HTTP_404_NOT_FOUND)

        if message.provider_message_id:
            from .providers import ProviderFactory
            provider_type = "whatsapp" if "wamid" in message.provider_message_id else "dummy"
            provider = ProviderFactory.get_provider(channel=message.channel, provider_name=provider_type)
            latest_status = provider.check_status(message.provider_message_id)

            service = get_communication_service()
            message = service.update_message_status(message.id, latest_status.value)

        return Response(MessageSerializer(message).data)


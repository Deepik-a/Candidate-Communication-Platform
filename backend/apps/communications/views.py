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
from .models import Message, MessageTemplate
from .services import CommunicationService
from .providers import ProviderFactory
from .templates import render_message_content, TEMPLATE_PLACEHOLDERS
from .serializers import (
    MessageSerializer,
    SendMessageSerializer,
    BulkSendMessageSerializer,
    BulkMessageResponseSerializer,
    CandidateMessageOutcomeSerializer,
    UpdateMessageStatusSerializer,
    WebhookStatusUpdateSerializer,
    MessageTemplateSerializer,
    TemplatePreviewSerializer,
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
            content=serializer.validated_data.get('content') or '',
            provider_name=serializer.validated_data.get('provider') or None,
            scheduled_at=serializer.validated_data.get('scheduled_at'),
            template_id=serializer.validated_data.get('template_id'),
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
            content=serializer.validated_data.get('content') or '',
            provider_name=serializer.validated_data.get('provider') or None,
            scheduled_at=serializer.validated_data.get('scheduled_at'),
            template_id=serializer.validated_data.get('template_id'),
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
    Actively polls the dummy provider for the latest message status and updates the database.
    """

    @extend_schema(
        responses={200: MessageSerializer},
        summary='Sync latest status directly from dummy provider',
    )
    def post(self, request, message_id):
        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return Response({'detail': 'Message not found.'}, status=status.HTTP_404_NOT_FOUND)

        service = get_communication_service()
        if message.provider_message_id:
            provider = ProviderFactory.get_provider(channel=message.channel, provider_name='dummy')
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
    Webhook receiver for the dummy communication provider.
    Receives status update callbacks and progresses message status: Sent → Delivered → Read.
    Idempotent: duplicate callbacks are handled gracefully (returns 200 with no side-effects).
    """

    @extend_schema(
        summary='Dummy provider webhook receiver',
        responses={200: dict},
    )
    def post(self, request):
        payload = request.data or {}

        # Parse dummy service webhook payload:
        # { "reference_id": "sent_XXXX", "status": "delivered" }
        # Also supports: provider_message_id, message_ref, id, message_id
        provider_msg_id = (
            payload.get("provider_message_id")
            or payload.get("reference_id")
            or payload.get("message_ref")
            or payload.get("id")
        )
        target_status = payload.get("status")
        raw_error = payload.get("error") or payload.get("error_message")

        # Direct message_id fallback
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

        # Always return 200 so external providers (e.g. dummy service) don't log FAIL.
        # Webhooks are fire-and-forget acknowledgements — the provider doesn't need error details.
        if not outcome.message:
            return Response(
                {"success": False, "detail": outcome.detail},
                status=status.HTTP_200_OK,
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


class MessageRetryView(APIView):
    """POST /api/v1/communications/messages/<id>/retry/ — retry a retryable failed message."""

    @extend_schema(responses={200: CandidateMessageOutcomeSerializer}, summary='Retry a failed message')
    def post(self, request, message_id):
        service = get_communication_service()
        outcome = service.retry_failed_message(message_id)
        if outcome.message_id is None:
            return Response({'detail': outcome.error_message}, status=status.HTTP_404_NOT_FOUND)
        http_status = status.HTTP_200_OK
        if not outcome.success and not outcome.is_retryable:
            http_status = status.HTTP_400_BAD_REQUEST
        return Response(CandidateMessageOutcomeSerializer(outcome).data, status=http_status)


class ProviderCatalogView(APIView):
    """GET /api/v1/communications/providers/ — available communication methods."""

    @extend_schema(summary='List communication providers')
    def get(self, request):
        return Response({'results': ProviderFactory.catalog()})


class CommunicationHealthView(APIView):
    """GET /api/v1/communications/health/ — provider health and delivery counters."""

    @extend_schema(summary='Communication service health')
    def get(self, request):
        service = get_communication_service()
        return Response(service.get_health_snapshot())


class DispatchScheduledView(APIView):
    """POST /api/v1/communications/dispatch-scheduled/ — send due scheduled messages."""

    @extend_schema(summary='Dispatch due scheduled messages')
    def post(self, request):
        service = get_communication_service()
        outcomes = service.dispatch_due_scheduled_messages()
        return Response({
            'dispatched': len(outcomes),
            'outcomes': CandidateMessageOutcomeSerializer(outcomes, many=True).data,
        })


class MessageTemplateListCreateView(APIView):
    """GET/POST /api/v1/communications/templates/"""

    @extend_schema(responses={200: MessageTemplateSerializer(many=True)}, summary='List message templates')
    def get(self, request):
        templates = MessageTemplate.objects.all()
        if not templates.exists():
            MessageTemplate.objects.bulk_create([
                MessageTemplate(
                    name='Interview invitation',
                    content='Hello {{full_name}}, your interview is scheduled. We will contact you at {{mobile_number}}.',
                    channel='sms',
                ),
                MessageTemplate(
                    name='Application received',
                    content='Hi {{full_name}} ({{candidate_id}}), we received your application. We will follow up at {{email}}.',
                    channel='email',
                ),
            ])
            templates = MessageTemplate.objects.all()
        return Response(MessageTemplateSerializer(templates, many=True).data)

    @extend_schema(request=MessageTemplateSerializer, responses={201: MessageTemplateSerializer}, summary='Create message template')
    def post(self, request):
        serializer = MessageTemplateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MessageTemplateDetailView(APIView):
    """GET/PATCH/DELETE /api/v1/communications/templates/<id>/"""

    def _get(self, template_id):
        try:
            return MessageTemplate.objects.get(id=template_id)
        except MessageTemplate.DoesNotExist:
            return None

    @extend_schema(responses={200: MessageTemplateSerializer})
    def get(self, request, template_id):
        template = self._get(template_id)
        if not template:
            return Response({'detail': 'Template not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(MessageTemplateSerializer(template).data)

    @extend_schema(request=MessageTemplateSerializer, responses={200: MessageTemplateSerializer})
    def patch(self, request, template_id):
        template = self._get(template_id)
        if not template:
            return Response({'detail': 'Template not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = MessageTemplateSerializer(template, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, template_id):
        template = self._get(template_id)
        if not template:
            return Response({'detail': 'Template not found.'}, status=status.HTTP_404_NOT_FOUND)
        template.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageTemplatePreviewView(APIView):
    """POST /api/v1/communications/templates/preview/ — interpolate placeholders for a candidate."""

    @extend_schema(request=TemplatePreviewSerializer, summary='Preview template with candidate data')
    def post(self, request):
        serializer = TemplatePreviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            candidate = Candidate.objects.get(id=serializer.validated_data['candidate_id'])
        except Candidate.DoesNotExist:
            return Response({'detail': 'Candidate not found.'}, status=status.HTTP_404_NOT_FOUND)

        content = serializer.validated_data.get('content') or ''
        template_id = serializer.validated_data.get('template_id')
        if template_id and not content:
            template = MessageTemplate.objects.filter(id=template_id).first()
            if not template:
                return Response({'detail': 'Template not found.'}, status=status.HTTP_404_NOT_FOUND)
            content = template.content

        return Response({
            'preview': render_message_content(content, candidate),
            'placeholders': [{'token': token, 'description': desc} for token, desc in TEMPLATE_PLACEHOLDERS],
        })

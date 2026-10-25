"""Communications API views."""

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema

from apps.candidates.infrastructure.models import Candidate, MessageStatus
from .models import Message, MessageStatusLog
from .serializers import MessageSerializer, SendMessageSerializer


class SendMessageView(APIView):
    """
    POST /api/v1/communications/send/
    Simulates sending a message to a candidate and logs it.
    """

    @extend_schema(
        request=SendMessageSerializer,
        responses={201: MessageSerializer},
        summary='Send a message to a candidate',
    )
    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            candidate = Candidate.objects.get(id=serializer.validated_data['candidate_id'])
        except Candidate.DoesNotExist:
            return Response({'detail': 'Candidate not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Create message log
        message = Message.objects.create(
            candidate=candidate,
            channel=serializer.validated_data['channel'],
            content=serializer.validated_data['content'],
            status=MessageStatusLog.SENT,
        )

        # Update candidate last message date and status
        candidate.last_message_date = timezone.now().date()
        candidate.status = MessageStatus.SENT
        candidate.save(update_fields=['last_message_date', 'status'])

        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class CandidateMessagesView(APIView):
    """GET /api/v1/communications/candidate/<candidate_id>/  — message history."""

    @extend_schema(responses={200: MessageSerializer(many=True)}, summary='Get message history for a candidate')
    def get(self, request, candidate_id):
        try:
            candidate = Candidate.objects.get(id=candidate_id)
        except Candidate.DoesNotExist:
            return Response({'detail': 'Candidate not found.'}, status=status.HTTP_404_NOT_FOUND)

        messages = Message.objects.filter(candidate=candidate)
        return Response(MessageSerializer(messages, many=True).data)

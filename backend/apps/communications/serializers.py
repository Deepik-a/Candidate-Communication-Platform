"""Communications serializers."""

from rest_framework import serializers
from .models import Message, MessageStatusLog, MessageChannel


class MessageSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.full_name', read_only=True)
    candidate_code = serializers.CharField(source='candidate.candidate_id', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id',
            'candidate',
            'candidate_name',
            'candidate_code',
            'channel',
            'content',
            'status',
            'provider',
            'provider_message_id',
            'error_message',
            'sent_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'provider', 'provider_message_id', 'error_message', 'sent_at', 'updated_at']


class SendMessageSerializer(serializers.Serializer):
    candidate_id = serializers.IntegerField()
    channel = serializers.ChoiceField(choices=MessageChannel.values, default=MessageChannel.SMS)
    content = serializers.CharField(min_length=1, max_length=2000)


class BulkSendMessageSerializer(serializers.Serializer):
    candidate_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
    )
    channel = serializers.ChoiceField(choices=MessageChannel.values, default=MessageChannel.SMS)
    content = serializers.CharField(min_length=1, max_length=2000)


class CandidateMessageOutcomeSerializer(serializers.Serializer):
    candidate_id = serializers.IntegerField()
    candidate_name = serializers.CharField()
    candidate_code = serializers.CharField()
    success = serializers.BooleanField()
    status = serializers.CharField()
    message_id = serializers.IntegerField(allow_null=True)
    provider = serializers.CharField()
    provider_message_id = serializers.CharField(allow_blank=True)
    error_message = serializers.CharField(allow_null=True)


class BulkMessageResponseSerializer(serializers.Serializer):
    total_requested = serializers.IntegerField()
    successful_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    outcomes = CandidateMessageOutcomeSerializer(many=True)


class UpdateMessageStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=MessageStatusLog.values)

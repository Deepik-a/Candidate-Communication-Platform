"""Communications serializers."""

from rest_framework import serializers
from .models import Message, MessageStatusLog, MessageChannel, MessageTemplate
from .failures import is_retryable_failure
from .templates import TEMPLATE_PLACEHOLDERS, render_message_content


class MessageSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.full_name', read_only=True)
    candidate_code = serializers.CharField(source='candidate.candidate_id', read_only=True)
    candidate_phone = serializers.CharField(source='candidate.mobile_number', read_only=True)
    candidate_email = serializers.CharField(source='candidate.email', read_only=True)
    is_retryable = serializers.SerializerMethodField()
    template_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id',
            'candidate',
            'candidate_name',
            'candidate_code',
            'candidate_phone',
            'candidate_email',
            'channel',
            'content',
            'status',
            'provider',
            'provider_message_id',
            'failure_category',
            'error_message',
            'scheduled_at',
            'template',
            'template_name',
            'retry_count',
            'is_retryable',
            'sent_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'candidate_name',
            'candidate_code',
            'candidate_phone',
            'candidate_email',
            'provider',
            'provider_message_id',
            'failure_category',
            'error_message',
            'retry_count',
            'is_retryable',
            'template_name',
            'sent_at',
            'updated_at',
        ]

    def get_is_retryable(self, obj) -> bool:
        return obj.status == MessageStatusLog.FAILED and is_retryable_failure(obj.failure_category)

    def get_template_name(self, obj):
        return obj.template.name if obj.template_id else None


class SendMessageSerializer(serializers.Serializer):
    candidate_id = serializers.IntegerField()
    channel = serializers.ChoiceField(choices=MessageChannel.values, default=MessageChannel.SMS)
    content = serializers.CharField(required=False, allow_blank=True, default='', max_length=2000)
    provider = serializers.CharField(required=False, allow_blank=True, default='')
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    template_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if not (attrs.get('content') or '').strip() and not attrs.get('template_id'):
            raise serializers.ValidationError({'content': 'Message content or a template is required.'})
        return attrs


class BulkSendMessageSerializer(serializers.Serializer):
    candidate_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
    )
    channel = serializers.ChoiceField(choices=MessageChannel.values, default=MessageChannel.SMS)
    content = serializers.CharField(required=False, allow_blank=True, default='', max_length=2000)
    provider = serializers.CharField(required=False, allow_blank=True, default='')
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    template_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if not (attrs.get('content') or '').strip() and not attrs.get('template_id'):
            raise serializers.ValidationError({'content': 'Message content or a template is required.'})
        return attrs


class CandidateMessageOutcomeSerializer(serializers.Serializer):
    candidate_id = serializers.IntegerField()
    candidate_name = serializers.CharField()
    candidate_code = serializers.CharField()
    success = serializers.BooleanField()
    status = serializers.CharField()
    message_id = serializers.IntegerField(allow_null=True)
    provider = serializers.CharField()
    provider_message_id = serializers.CharField(allow_blank=True)
    failure_category = serializers.CharField(allow_null=True, required=False)
    error_message = serializers.CharField(allow_null=True)
    is_retryable = serializers.BooleanField(required=False)


class BulkMessageResponseSerializer(serializers.Serializer):
    total_requested = serializers.IntegerField()
    successful_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    outcomes = CandidateMessageOutcomeSerializer(many=True)


class UpdateMessageStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=MessageStatusLog.values)
    error = serializers.CharField(required=False, allow_blank=True, default='')


class WebhookStatusUpdateSerializer(serializers.Serializer):
    """Universal webhook payload adapter for external provider status callbacks."""
    reference_id = serializers.CharField(required=False, allow_blank=True, default='')
    provider_message_id = serializers.CharField(required=False, allow_blank=True, default='')
    message_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    status = serializers.CharField(required=False, default='delivered')
    error = serializers.CharField(required=False, allow_blank=True, default='')


class MessageTemplateSerializer(serializers.ModelSerializer):
    placeholders = serializers.SerializerMethodField()

    class Meta:
        model = MessageTemplate
        fields = ['id', 'name', 'content', 'channel', 'placeholders', 'created_at', 'updated_at']
        read_only_fields = ['id', 'placeholders', 'created_at', 'updated_at']

    def get_placeholders(self, obj):
        return [{'token': token, 'description': desc} for token, desc in TEMPLATE_PLACEHOLDERS]


class TemplatePreviewSerializer(serializers.Serializer):
    candidate_id = serializers.IntegerField()
    content = serializers.CharField(required=False, allow_blank=True, default='')
    template_id = serializers.IntegerField(required=False, allow_null=True)

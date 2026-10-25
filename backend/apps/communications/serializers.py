"""Communications serializers."""

from rest_framework import serializers
from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.full_name', read_only=True)
    candidate_code = serializers.CharField(source='candidate.candidate_id', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'candidate', 'candidate_name', 'candidate_code',
                  'channel', 'content', 'status', 'sent_at', 'updated_at']
        read_only_fields = ['id', 'sent_at', 'updated_at']


class SendMessageSerializer(serializers.Serializer):
    candidate_id = serializers.IntegerField()
    channel = serializers.ChoiceField(choices=['sms', 'whatsapp', 'email'])
    content = serializers.CharField(min_length=1, max_length=2000)

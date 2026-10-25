"""
DRF Serializers for Candidate API.
Presentation layer — handles input/output transformation.
"""

from rest_framework import serializers
from apps.candidates.infrastructure.models import Candidate, MessageStatus


class CandidateSerializer(serializers.ModelSerializer):
    """Full candidate serializer."""

    class Meta:
        model = Candidate
        fields = [
            'id',
            'candidate_id',
            'full_name',
            'mobile_number',
            'email',
            'last_message_date',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'candidate_id', 'created_at', 'updated_at']


class CandidateCreateSerializer(serializers.Serializer):
    """Serializer for creating a new candidate."""
    full_name = serializers.CharField(max_length=255)
    mobile_number = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)

    def validate_mobile_number(self, value):
        if Candidate.objects.filter(mobile_number=value).exists():
            raise serializers.ValidationError("A candidate with this mobile number already exists.")
        return value


class CandidateUpdateSerializer(serializers.Serializer):
    """Serializer for partial update of a candidate."""
    full_name = serializers.CharField(max_length=255, required=False)
    mobile_number = serializers.CharField(max_length=20, required=False)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)


class BulkDeleteSerializer(serializers.Serializer):
    """Serializer for bulk-deleting candidates."""
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
    )


class CandidateListResponseSerializer(serializers.Serializer):
    """Paginated response wrapper."""
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    results = CandidateSerializer(many=True)

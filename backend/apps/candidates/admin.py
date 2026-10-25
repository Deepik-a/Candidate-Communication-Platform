"""
Django admin registration for Candidate and Message models.
"""

from django.contrib import admin
from apps.candidates.infrastructure.models import Candidate


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['candidate_id', 'full_name', 'mobile_number', 'status', 'last_message_date', 'created_at']
    list_filter = ['status']
    search_fields = ['full_name', 'mobile_number', 'candidate_id']
    readonly_fields = ['candidate_id', 'created_at', 'updated_at']
    ordering = ['-created_at']

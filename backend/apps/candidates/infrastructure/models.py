"""
Django ORM model for Candidate.
Infrastructure layer — framework-specific implementation.
"""

import uuid
import random
import string
from django.db import models
from django.utils import timezone


def generate_candidate_id():
    """Generate a unique alphanumeric ID like A1B2C3."""
    chars = string.ascii_uppercase + string.digits
    while True:
        candidate_id = ''.join(random.choices(chars, k=6))
        if not Candidate.objects.filter(candidate_id=candidate_id).exists():
            return candidate_id


class MessageStatus(models.TextChoices):
    DELIVERED = 'delivered', 'Delivered'
    READ = 'read', 'Read'
    SENT = 'sent', 'Sent'
    FAILED = 'failed', 'Failed'
    NA = 'NA', 'NA'


class Candidate(models.Model):
    """ORM model for candidate."""

    candidate_id = models.CharField(
        max_length=10,
        unique=True,
        default=generate_candidate_id,
        editable=False,
        db_index=True,
    )
    full_name = models.CharField(max_length=255)
    mobile_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)
    last_message_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=MessageStatus.choices,
        default=MessageStatus.NA,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'candidates'
        ordering = ['-created_at']
        verbose_name = 'Candidate'
        verbose_name_plural = 'Candidates'

    def __str__(self):
        return f"{self.full_name} ({self.candidate_id})"

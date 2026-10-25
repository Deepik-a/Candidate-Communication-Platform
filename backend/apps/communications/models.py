"""Communication ORM models."""

from django.db import models
from apps.candidates.infrastructure.models import Candidate


class MessageChannel(models.TextChoices):
    SMS = 'sms', 'SMS'
    WHATSAPP = 'whatsapp', 'WhatsApp'
    EMAIL = 'email', 'Email'


class MessageStatusLog(models.TextChoices):
    PENDING = 'pending', 'Pending'
    SENT = 'sent', 'Sent'
    DELIVERED = 'delivered', 'Delivered'
    READ = 'read', 'Read'
    FAILED = 'failed', 'Failed'


class Message(models.Model):
    """Tracks each message sent to a candidate."""
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='messages')
    channel = models.CharField(max_length=20, choices=MessageChannel.choices, default=MessageChannel.SMS)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=MessageStatusLog.choices, default=MessageStatusLog.PENDING)
    sent_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messages'
        ordering = ['-sent_at']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        return f"[{self.channel}] {self.candidate.full_name} — {self.status}"

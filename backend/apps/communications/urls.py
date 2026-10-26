"""URL routes for communications app."""

from django.urls import path
from .views import (
    SendMessageView,
    BulkSendMessageView,
    CandidateMessagesView,
    MessageDetailStatusView,
    MessageSyncStatusView,
    ProviderWebhookView,
)

urlpatterns = [
    path('communications/send/', SendMessageView.as_view(), name='send-message'),
    path('communications/bulk-send/', BulkSendMessageView.as_view(), name='bulk-send-message'),
    path('communications/candidate/<int:candidate_id>/', CandidateMessagesView.as_view(), name='candidate-messages'),
    path('communications/messages/<int:message_id>/', MessageDetailStatusView.as_view(), name='message-detail-status'),
    path('communications/messages/<int:message_id>/sync/', MessageSyncStatusView.as_view(), name='message-sync-status'),
    path('communications/webhook/', ProviderWebhookView.as_view(), name='provider-webhook'),
]

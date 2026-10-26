"""URL routes for communications app."""

from django.urls import path
from .views import (
    SendMessageView,
    BulkSendMessageView,
    CandidateMessagesView,
    MessageDetailStatusView,
    MessageSyncStatusView,
    ProviderWebhookView,
    MessageRetryView,
    ProviderCatalogView,
    CommunicationHealthView,
    DispatchScheduledView,
    MessageTemplateListCreateView,
    MessageTemplateDetailView,
    MessageTemplatePreviewView,
)

urlpatterns = [
    path('communications/send/', SendMessageView.as_view(), name='send-message'),
    path('communications/bulk-send/', BulkSendMessageView.as_view(), name='bulk-send-message'),
    path('communications/candidate/<int:candidate_id>/', CandidateMessagesView.as_view(), name='candidate-messages'),
    path('communications/messages/<int:message_id>/', MessageDetailStatusView.as_view(), name='message-detail-status'),
    path('communications/messages/<int:message_id>/sync/', MessageSyncStatusView.as_view(), name='message-sync-status'),
    path('communications/messages/<int:message_id>/retry/', MessageRetryView.as_view(), name='message-retry'),
    path('communications/webhook/', ProviderWebhookView.as_view(), name='provider-webhook'),
    path('communications/providers/', ProviderCatalogView.as_view(), name='communication-providers'),
    path('communications/health/', CommunicationHealthView.as_view(), name='communication-health'),
    path('communications/dispatch-scheduled/', DispatchScheduledView.as_view(), name='dispatch-scheduled'),
    path('communications/templates/', MessageTemplateListCreateView.as_view(), name='message-templates'),
    path('communications/templates/preview/', MessageTemplatePreviewView.as_view(), name='message-template-preview'),
    path('communications/templates/<int:template_id>/', MessageTemplateDetailView.as_view(), name='message-template-detail'),
]

"""URL routes for communications app."""

from django.urls import path
from .views import SendMessageView, CandidateMessagesView

urlpatterns = [
    path('communications/send/', SendMessageView.as_view(), name='send-message'),
    path('communications/candidate/<int:candidate_id>/', CandidateMessagesView.as_view(), name='candidate-messages'),
]

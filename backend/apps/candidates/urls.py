"""URL routes for candidates app."""

from django.urls import path
from .api.views import CandidateListCreateView, CandidateDetailView, CandidateBulkDeleteView

urlpatterns = [
    path('candidates/', CandidateListCreateView.as_view(), name='candidate-list-create'),
    path('candidates/<int:pk>/', CandidateDetailView.as_view(), name='candidate-detail'),
    path('candidates/bulk-delete/', CandidateBulkDeleteView.as_view(), name='candidate-bulk-delete'),
]

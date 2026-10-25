"""
DRF Views for Candidate API.
Presentation layer — thin controllers, delegates logic to service.
"""

import math
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.candidates.application.services import CandidateService
from apps.candidates.infrastructure.repositories import DjangoCandidateRepository
from apps.candidates.infrastructure.models import Candidate
from .serializers import (
    CandidateSerializer,
    CandidateCreateSerializer,
    CandidateUpdateSerializer,
    BulkDeleteSerializer,
)


def get_candidate_service() -> CandidateService:
    """Factory function — dependency injection for the service."""
    repository = DjangoCandidateRepository()
    return CandidateService(repository=repository)


class CandidateListCreateView(APIView):
    """
    GET  /api/v1/candidates/  — list candidates (paginated, searchable)
    POST /api/v1/candidates/  — create a new candidate
    """

    @extend_schema(
        parameters=[
            OpenApiParameter('search', str, description='Search by name, mobile, or ID'),
            OpenApiParameter('page', int, default=1),
            OpenApiParameter('page_size', int, default=10),
        ],
        responses={200: CandidateSerializer(many=True)},
        summary='List all candidates',
    )
    def get(self, request):
        service = get_candidate_service()
        search = request.query_params.get('search', None)
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))

        entities, total = service.list_candidates(search=search, page=page, page_size=page_size)

        # Map back to ORM for serialization
        ids = [e.id for e in entities]
        orm_map = {c.id: c for c in Candidate.objects.filter(id__in=ids)}
        ordered = [orm_map[e.id] for e in entities if e.id in orm_map]

        serializer = CandidateSerializer(ordered, many=True)
        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(total / page_size) if page_size else 1,
            'results': serializer.data,
        })

    @extend_schema(
        request=CandidateCreateSerializer,
        responses={201: CandidateSerializer},
        summary='Create a new candidate',
    )
    def post(self, request):
        serializer = CandidateCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        service = get_candidate_service()
        entity = service.create_candidate(
            full_name=serializer.validated_data['full_name'],
            mobile_number=serializer.validated_data['mobile_number'],
            email=serializer.validated_data.get('email'),
        )
        candidate = Candidate.objects.get(id=entity.id)
        return Response(CandidateSerializer(candidate).data, status=status.HTTP_201_CREATED)


class CandidateDetailView(APIView):
    """
    GET    /api/v1/candidates/<id>/  — retrieve
    PATCH  /api/v1/candidates/<id>/  — partial update
    DELETE /api/v1/candidates/<id>/  — delete
    """

    @extend_schema(responses={200: CandidateSerializer}, summary='Retrieve candidate')
    def get(self, request, pk):
        service = get_candidate_service()
        entity = service.get_candidate(pk)
        if not entity:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        candidate = Candidate.objects.get(id=pk)
        return Response(CandidateSerializer(candidate).data)

    @extend_schema(
        request=CandidateUpdateSerializer,
        responses={200: CandidateSerializer},
        summary='Update candidate',
    )
    def patch(self, request, pk):
        serializer = CandidateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        service = get_candidate_service()
        entity = service.update_candidate(pk, **serializer.validated_data)
        if not entity:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        candidate = Candidate.objects.get(id=pk)
        return Response(CandidateSerializer(candidate).data)

    @extend_schema(responses={204: None}, summary='Delete candidate')
    def delete(self, request, pk):
        service = get_candidate_service()
        deleted = service.delete_candidate(pk)
        if not deleted:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CandidateBulkDeleteView(APIView):
    """POST /api/v1/candidates/bulk-delete/ — delete multiple candidates."""

    @extend_schema(
        request=BulkDeleteSerializer,
        responses={200: {'type': 'object', 'properties': {'deleted': {'type': 'integer'}}}},
        summary='Bulk delete candidates',
    )
    def post(self, request):
        serializer = BulkDeleteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        service = get_candidate_service()
        count = service.bulk_delete_candidates(serializer.validated_data['ids'])
        return Response({'deleted': count})

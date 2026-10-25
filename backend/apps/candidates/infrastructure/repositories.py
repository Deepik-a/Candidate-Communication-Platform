"""
Django ORM implementation of the CandidateRepository.
Infrastructure layer — implements the domain interface.
"""

from typing import List, Optional, Tuple
from django.db.models import Q

from apps.candidates.domain.entities import CandidateEntity, MessageStatus as DomainStatus
from apps.candidates.domain.repositories import CandidateRepositoryInterface
from .models import Candidate


class DjangoCandidateRepository(CandidateRepositoryInterface):
    """Concrete implementation using Django ORM."""

    def _to_entity(self, model: Candidate) -> CandidateEntity:
        return CandidateEntity(
            id=model.id,
            candidate_id=model.candidate_id,
            full_name=model.full_name,
            mobile_number=model.mobile_number,
            email=model.email,
            last_message_date=model.last_message_date,
            status=DomainStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model_data(self, entity: CandidateEntity) -> dict:
        return {
            'full_name': entity.full_name,
            'mobile_number': entity.mobile_number,
            'email': entity.email,
            'last_message_date': entity.last_message_date,
            'status': entity.status.value,
        }

    def get_all(
        self,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[CandidateEntity], int]:
        qs = Candidate.objects.all()
        if search:
            qs = qs.filter(
                Q(full_name__icontains=search) |
                Q(mobile_number__icontains=search) |
                Q(email__icontains=search) |
                Q(candidate_id__icontains=search)
            )
        total = qs.count()
        offset = (page - 1) * page_size
        qs = qs[offset:offset + page_size]
        return [self._to_entity(c) for c in qs], total

    def get_by_id(self, candidate_id: int) -> Optional[CandidateEntity]:
        try:
            model = Candidate.objects.get(id=candidate_id)
            return self._to_entity(model)
        except Candidate.DoesNotExist:
            return None

    def get_by_candidate_code(self, candidate_code: str) -> Optional[CandidateEntity]:
        try:
            model = Candidate.objects.get(candidate_id=candidate_code)
            return self._to_entity(model)
        except Candidate.DoesNotExist:
            return None

    def create(self, entity: CandidateEntity) -> CandidateEntity:
        data = self._to_model_data(entity)
        model = Candidate.objects.create(**data)
        return self._to_entity(model)

    def update(self, entity: CandidateEntity) -> CandidateEntity:
        data = self._to_model_data(entity)
        Candidate.objects.filter(id=entity.id).update(**data)
        model = Candidate.objects.get(id=entity.id)
        return self._to_entity(model)

    def delete(self, candidate_id: int) -> bool:
        deleted, _ = Candidate.objects.filter(id=candidate_id).delete()
        return deleted > 0

    def bulk_delete(self, ids: List[int]) -> int:
        deleted, _ = Candidate.objects.filter(id__in=ids).delete()
        return deleted

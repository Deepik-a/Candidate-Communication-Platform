"""
Repository interface (port) for the candidates domain.
Following Dependency Inversion Principle (DIP).
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from .entities import CandidateEntity


class CandidateRepositoryInterface(ABC):
    """Abstract repository — defines the contract. No implementation details."""

    @abstractmethod
    def get_all(
        self,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[CandidateEntity], int]:
        """Return paginated list of candidates and total count."""
        ...

    @abstractmethod
    def get_by_id(self, candidate_id: int) -> Optional[CandidateEntity]:
        ...

    @abstractmethod
    def get_by_candidate_code(self, candidate_code: str) -> Optional[CandidateEntity]:
        ...

    @abstractmethod
    def create(self, entity: CandidateEntity) -> CandidateEntity:
        ...

    @abstractmethod
    def update(self, entity: CandidateEntity) -> CandidateEntity:
        ...

    @abstractmethod
    def delete(self, candidate_id: int) -> bool:
        ...

    @abstractmethod
    def bulk_delete(self, ids: List[int]) -> int:
        """Returns number of deleted records."""
        ...

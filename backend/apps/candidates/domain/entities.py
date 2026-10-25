"""
Candidate domain model — pure Python, no Django dependencies.
Following Clean Architecture: entities are framework-agnostic.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class MessageStatus(str, Enum):
    READ = "read"
    SENT = "sent"
    FAILED = "failed"
    NA = "NA"


@dataclass
class CandidateEntity:
    """Core candidate entity — business rules live here."""
    id: Optional[int]
    candidate_id: str          # e.g. A1B2C3
    full_name: str
    mobile_number: str
    email: Optional[str]
    last_message_date: Optional[datetime]
    status: MessageStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def has_been_contacted(self) -> bool:
        return self.last_message_date is not None

    def is_status_failed(self) -> bool:
        return self.status == MessageStatus.FAILED

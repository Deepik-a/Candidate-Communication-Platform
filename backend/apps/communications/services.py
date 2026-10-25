"""
Communication Application Services.
Coordinates sending individual and bulk messages, status updates, and candidate synchronization.
Following Single Responsibility Principle and Dependency Inversion Principle.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from django.utils import timezone
from apps.candidates.infrastructure.models import Candidate, MessageStatus
from .models import Message, MessageStatusLog
from .domain import CommunicationProvider, DeliveryStatus, ProviderMessageResult
from .providers import ProviderFactory


@dataclass
class CandidateMessageOutcome:
    """Outcome for a single candidate in bulk or single messaging."""
    candidate_id: int
    candidate_name: str
    candidate_code: str
    success: bool
    status: str
    message_id: Optional[int]
    provider: str
    provider_message_id: str
    error_message: Optional[str]


@dataclass
class BulkMessageResult:
    """Aggregate result for bulk message dispatch."""
    total_requested: int
    successful_count: int
    failed_count: int
    outcomes: List[CandidateMessageOutcome]


class CommunicationService:
    """
    Application Service for sending and tracking messages.
    Adheres to Clean Architecture:
    - Depends on abstraction (CommunicationProvider) injected via constructor or factory
    - Handles independent candidate processing for bulk operations
    - Keeps candidate status and message logs synchronized
    """

    def __init__(self, provider: Optional[CommunicationProvider] = None):
        self._provider = provider

    def _resolve_provider(self, channel: str) -> CommunicationProvider:
        if self._provider is not None:
            return self._provider
        return ProviderFactory.get_provider(channel=channel, provider_name="gateway")

    def send_single_message(
        self,
        candidate_id: int,
        channel: str,
        content: str,
        forced_status: Optional[str] = None,
    ) -> CandidateMessageOutcome:
        """
        Sends a message to an individual candidate through the provider.
        Records the communication and updates the candidate's last message date & status.
        """
        try:
            candidate = Candidate.objects.get(id=candidate_id)
        except Candidate.DoesNotExist:
            return CandidateMessageOutcome(
                candidate_id=candidate_id,
                candidate_name="Unknown",
                candidate_code="",
                success=False,
                status=MessageStatusLog.FAILED,
                message_id=None,
                provider="none",
                provider_message_id="",
                error_message=f"Candidate with id {candidate_id} does not exist.",
            )

        provider = self._resolve_provider(channel)
        recipient = candidate.email if channel == 'email' and candidate.email else candidate.mobile_number

        # Dispatch via provider
        provider_result: ProviderMessageResult = provider.send(
            recipient=recipient,
            content=content,
            channel=channel,
        )

        final_status = forced_status or provider_result.status.value

        # Create persistent message record
        message = Message.objects.create(
            candidate=candidate,
            channel=channel,
            content=content,
            status=final_status,
            provider=provider_result.provider_name,
            provider_message_id=provider_result.provider_message_id,
            error_message=provider_result.error_message or '',
        )

        # Update candidate state
        candidate.last_message_date = timezone.now().date()
        # Map message status to candidate status
        if final_status == MessageStatusLog.READ:
            candidate.status = MessageStatus.READ
        elif final_status == MessageStatusLog.DELIVERED:
            candidate.status = MessageStatus.DELIVERED
        elif final_status == MessageStatusLog.FAILED:
            candidate.status = MessageStatus.FAILED
        else:
            candidate.status = MessageStatus.SENT
        candidate.save(update_fields=['last_message_date', 'status'])

        return CandidateMessageOutcome(
            candidate_id=candidate.id,
            candidate_name=candidate.full_name,
            candidate_code=candidate.candidate_id,
            success=provider_result.success and final_status != MessageStatusLog.FAILED,
            status=final_status,
            message_id=message.id,
            provider=provider_result.provider_name,
            provider_message_id=provider_result.provider_message_id,
            error_message=provider_result.error_message,
        )

    def send_bulk_messages(
        self,
        candidate_ids: List[int],
        channel: str,
        content: str,
    ) -> BulkMessageResult:
        """
        Sends the same message to multiple candidates.
        Requirement #4:
        - Each candidate's message is tracked independently.
        - One candidate's failure does not prevent the remaining messages from being processed.
        - Clearly returns individual result for each candidate.
        """
        outcomes: List[CandidateMessageOutcome] = []
        successful_count = 0
        failed_count = 0

        for cid in candidate_ids:
            try:
                outcome = self.send_single_message(
                    candidate_id=cid,
                    channel=channel,
                    content=content,
                )
                outcomes.append(outcome)
                if outcome.success:
                    successful_count += 1
                else:
                    failed_count += 1
            except Exception as ex:
                failed_count += 1
                outcomes.append(
                    CandidateMessageOutcome(
                        candidate_id=cid,
                        candidate_name="Unknown",
                        candidate_code="",
                        success=False,
                        status=MessageStatusLog.FAILED,
                        message_id=None,
                        provider="error",
                        provider_message_id="",
                        error_message=str(ex),
                    )
                )

        return BulkMessageResult(
            total_requested=len(candidate_ids),
            successful_count=successful_count,
            failed_count=failed_count,
            outcomes=outcomes,
        )

    def update_message_status(self, message_id: int, new_status: str) -> Optional[Message]:
        """Update message status and update candidate's corresponding status."""
        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return None

        message.status = new_status
        message.save(update_fields=['status', 'updated_at'])

        # Keep candidate in sync with latest message status
        candidate = message.candidate
        if new_status == MessageStatusLog.READ:
            candidate.status = MessageStatus.READ
        elif new_status == MessageStatusLog.DELIVERED:
            candidate.status = MessageStatus.DELIVERED
        elif new_status == MessageStatusLog.FAILED:
            candidate.status = MessageStatus.FAILED
        elif new_status == MessageStatusLog.SENT:
            candidate.status = MessageStatus.SENT
        candidate.save(update_fields=['status'])

        return message

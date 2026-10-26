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
from .failures import CommunicationFailureTranslator, FailureCategory

# Status Progression Precedence hierarchy:
# pending (0) -> sent (1) -> delivered (2) -> read (3)
STATUS_PRECEDENCE = {
    MessageStatusLog.PENDING: 0,
    MessageStatusLog.SENT: 1,
    MessageStatusLog.DELIVERED: 2,
    MessageStatusLog.READ: 3,
}


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
    failure_category: Optional[str]
    error_message: Optional[str]


@dataclass
class BulkMessageResult:
    """Aggregate result for bulk message dispatch."""
    total_requested: int
    successful_count: int
    failed_count: int
    outcomes: List[CandidateMessageOutcome]


@dataclass
class StatusUpdateOutcome:
    """Outcome of an idempotent status update operation."""
    message: Optional[Message]
    status: str
    updated: bool
    was_duplicate: bool
    detail: str


class CommunicationService:
    """
    Application Service for sending and tracking messages.
    Adheres to Clean Architecture:
    - Depends on abstraction (CommunicationProvider) injected via constructor or factory
    - Handles independent candidate processing for bulk operations
    - Idempotent status updates with strict progression enforcement
    - Meaningful failure translation for recruiters
    """

    def __init__(self, provider: Optional[CommunicationProvider] = None):
        self._provider = provider

    def _resolve_provider(self, channel: str, provider_name: Optional[str] = None) -> CommunicationProvider:
        if self._provider is not None:
            return self._provider
        return ProviderFactory.get_provider(channel=channel, provider_name=provider_name)

    def send_single_message(
        self,
        candidate_id: int,
        channel: str,
        content: str,
        provider_name: Optional[str] = None,
        forced_status: Optional[str] = None,
    ) -> CandidateMessageOutcome:
        """
        Sends a message to an individual candidate through the provider.
        Records the communication and updates the candidate's journey status.
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
                failure_category=FailureCategory.INVALID_RECIPIENT.value,
                error_message=f"Candidate with id {candidate_id} does not exist in the database.",
            )

        recipient = (candidate.email if channel == 'email' and candidate.email else candidate.mobile_number) or ""

        # Validate recipient presence and basic format before contacting provider
        if not recipient or (channel in ('sms', 'whatsapp') and not CommunicationFailureTranslator._is_valid_phone(recipient)):
            analysis = CommunicationFailureTranslator.translate(
                channel=channel,
                recipient=recipient,
                raw_error="Missing or invalid recipient contact details.",
            )
            message = Message.objects.create(
                candidate=candidate,
                channel=channel,
                content=content,
                status=MessageStatusLog.FAILED,
                provider=provider_name or "validation-guard",
                provider_message_id="",
                failure_category=analysis.category.value,
                error_message=analysis.recruiter_message,
            )
            candidate.last_message_date = timezone.now().date()
            candidate.status = MessageStatus.FAILED
            candidate.save(update_fields=['last_message_date', 'status'])

            return CandidateMessageOutcome(
                candidate_id=candidate.id,
                candidate_name=candidate.full_name,
                candidate_code=candidate.candidate_id,
                success=False,
                status=MessageStatusLog.FAILED,
                message_id=message.id,
                provider=message.provider,
                provider_message_id="",
                failure_category=analysis.category.value,
                error_message=analysis.recruiter_message,
            )

        provider = self._resolve_provider(channel, provider_name=provider_name)

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
            failure_category=provider_result.failure_category or '',
            error_message=provider_result.error_message or '',
        )

        # Update candidate state
        candidate.last_message_date = timezone.now().date()
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
            failure_category=provider_result.failure_category or None,
            error_message=provider_result.error_message,
        )

    def send_bulk_messages(
        self,
        candidate_ids: List[int],
        channel: str,
        content: str,
        provider_name: Optional[str] = None,
    ) -> BulkMessageResult:
        """
        Sends the same message to multiple candidates.
        Requirement #4:
        - Each candidate's message is tracked independently.
        - One candidate's failure does not prevent remaining messages from being processed.
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
                    provider_name=provider_name,
                )
                outcomes.append(outcome)
                if outcome.success:
                    successful_count += 1
                else:
                    failed_count += 1
            except Exception as ex:
                failed_count += 1
                analysis = CommunicationFailureTranslator.translate(
                    channel=channel,
                    exception=ex,
                )
                outcomes.append(
                    CandidateMessageOutcome(
                        candidate_id=cid,
                        candidate_name="Unknown",
                        candidate_code="",
                        success=False,
                        status=MessageStatusLog.FAILED,
                        message_id=None,
                        provider="error-handler",
                        provider_message_id="",
                        failure_category=analysis.category.value,
                        error_message=analysis.recruiter_message,
                    )
                )

        return BulkMessageResult(
            total_requested=len(candidate_ids),
            successful_count=successful_count,
            failed_count=failed_count,
            outcomes=outcomes,
        )

    def update_message_status(
        self,
        message_id: Optional[int] = None,
        provider_message_id: Optional[str] = None,
        new_status: str = "",
        raw_error: Optional[str] = None,
    ) -> StatusUpdateOutcome:
        """
        Requirement #7:
        Updates message status upon receiving provider callbacks or webhook updates.
        Implements:
        - Progression hierarchy: Sent -> Delivered -> Read
        - Idempotency: Duplicate updates handled cleanly without errors or side-effects.
        - Anti-regression: Prevents an out-of-order callback (e.g. Sent) from reverting Delivered/Read.
        - Recruiter notification & Candidate journey synchronization.
        """
        # 1. Lookup message
        message = None
        if message_id:
            try:
                message = Message.objects.select_related('candidate').get(id=message_id)
            except Message.DoesNotExist:
                pass

        if not message and provider_message_id:
            message = Message.objects.select_related('candidate').filter(
                provider_message_id=provider_message_id
            ).first()

        if not message:
            return StatusUpdateOutcome(
                message=None,
                status=new_status,
                updated=False,
                was_duplicate=False,
                detail=f"Message not found (ID: {message_id}, Provider ID: {provider_message_id}).",
            )

        norm_status = (new_status or "").strip().lower()

        # Map common provider aliases
        alias_map = {
            "received": MessageStatusLog.DELIVERED,
            "undelivered": MessageStatusLog.FAILED,
            "error": MessageStatusLog.FAILED,
            "rejected": MessageStatusLog.FAILED,
        }
        target_status = alias_map.get(norm_status, norm_status)

        # 2. Duplicate detection (Idempotency)
        if message.status == target_status:
            return StatusUpdateOutcome(
                message=message,
                status=message.status,
                updated=False,
                was_duplicate=True,
                detail=f"Duplicate update: Message #{message.id} is already in '{target_status}' status.",
            )

        # 3. Hierarchy / Anti-regression check
        current_rank = STATUS_PRECEDENCE.get(message.status)
        new_rank = STATUS_PRECEDENCE.get(target_status)

        if current_rank is not None and new_rank is not None:
            if new_rank < current_rank:
                return StatusUpdateOutcome(
                    message=message,
                    status=message.status,
                    updated=False,
                    was_duplicate=False,
                    detail=(
                        f"Out-of-order update ignored: Current status '{message.status}' has higher precedence "
                        f"than incoming '{target_status}'."
                    ),
                )

        # If incoming is FAILED but message was already DELIVERED or READ
        if target_status == MessageStatusLog.FAILED:
            if message.status in (MessageStatusLog.DELIVERED, MessageStatusLog.READ):
                return StatusUpdateOutcome(
                    message=message,
                    status=message.status,
                    updated=False,
                    was_duplicate=False,
                    detail=f"Late failure ignored: Message #{message.id} was already confirmed '{message.status}'.",
                )

            # Classify failure meaningfully
            analysis = CommunicationFailureTranslator.translate(
                channel=message.channel,
                recipient=message.candidate.mobile_number,
                raw_error=raw_error or "Delivery failed according to communication provider callback.",
            )
            message.failure_category = analysis.category.value
            message.error_message = analysis.recruiter_message
        else:
            # Clear error upon successful transition
            message.failure_category = ""
            message.error_message = ""

        # Apply update
        message.status = target_status
        message.save(update_fields=['status', 'failure_category', 'error_message', 'updated_at'])

        # Keep candidate journey status synchronized
        candidate = message.candidate
        if target_status == MessageStatusLog.READ:
            candidate.status = MessageStatus.READ
        elif target_status == MessageStatusLog.DELIVERED:
            if candidate.status != MessageStatus.READ:
                candidate.status = MessageStatus.DELIVERED
        elif target_status == MessageStatusLog.FAILED:
            candidate.status = MessageStatus.FAILED
        elif target_status == MessageStatusLog.SENT:
            if candidate.status not in (MessageStatus.DELIVERED, MessageStatus.READ):
                candidate.status = MessageStatus.SENT
        candidate.save(update_fields=['status'])

        return StatusUpdateOutcome(
            message=message,
            status=target_status,
            updated=True,
            was_duplicate=False,
            detail=f"Successfully updated message #{message.id} status to '{target_status}'.",
        )

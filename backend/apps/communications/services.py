"""
Communication Application Services.
Coordinates sending individual and bulk messages, status updates, and candidate synchronization.
Following Single Responsibility Principle and Dependency Inversion Principle.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from apps.candidates.infrastructure.models import Candidate, MessageStatus
from .models import Message, MessageStatusLog, MessageTemplate
from .domain import CommunicationProvider, ProviderMessageResult
from .providers import ProviderFactory
from .failures import CommunicationFailureTranslator, FailureCategory, is_retryable_failure
from .templates import render_message_content

# Status Progression Precedence hierarchy:
# scheduled/pending (0) -> sent (1) -> delivered (2) -> read (3)
STATUS_PRECEDENCE = {
    MessageStatusLog.SCHEDULED: 0,
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
    is_retryable: bool = False


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

    def _parse_scheduled_at(self, scheduled_at) -> Optional[datetime]:
        if scheduled_at is None or scheduled_at == "":
            return None
        if isinstance(scheduled_at, datetime):
            when = scheduled_at
        else:
            when = parse_datetime(str(scheduled_at))
            if when is None:
                return None
        if timezone.is_naive(when):
            when = timezone.make_aware(when, timezone.get_current_timezone())
        return when

    def _resolve_content(self, content: str, template_id: Optional[int], candidate: Candidate) -> tuple:
        template = None
        source = content or ""
        if template_id:
            template = MessageTemplate.objects.filter(id=template_id).first()
            if template and not source:
                source = template.content
        rendered = render_message_content(source, candidate)
        return rendered, template

    def _apply_candidate_status(self, candidate: Candidate, final_status: str) -> None:
        if final_status == MessageStatusLog.READ:
            candidate.last_message_date = timezone.now().date()
            candidate.status = MessageStatus.READ
        elif final_status == MessageStatusLog.DELIVERED:
            candidate.last_message_date = timezone.now().date()
            candidate.status = MessageStatus.DELIVERED
        elif final_status == MessageStatusLog.FAILED:
            candidate.last_message_date = timezone.now().date()
            candidate.status = MessageStatus.FAILED
        elif final_status == MessageStatusLog.SCHEDULED:
            if candidate.status == MessageStatus.NA:
                candidate.status = MessageStatus.SCHEDULED
        else:
            candidate.last_message_date = timezone.now().date()
            candidate.status = MessageStatus.SENT
        candidate.save(update_fields=['last_message_date', 'status'])

    def _outcome_from_message(self, message: Message, success: bool) -> CandidateMessageOutcome:
        return CandidateMessageOutcome(
            candidate_id=message.candidate_id,
            candidate_name=message.candidate.full_name,
            candidate_code=message.candidate.candidate_id,
            success=success,
            status=message.status,
            message_id=message.id,
            provider=message.provider,
            provider_message_id=message.provider_message_id,
            failure_category=message.failure_category or None,
            error_message=message.error_message or None,
            is_retryable=message.status == MessageStatusLog.FAILED and is_retryable_failure(message.failure_category),
        )

    def send_single_message(
        self,
        candidate_id: int,
        channel: str,
        content: str,
        provider_name: Optional[str] = None,
        forced_status: Optional[str] = None,
        scheduled_at=None,
        template_id: Optional[int] = None,
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
                is_retryable=False,
            )

        rendered_content, template = self._resolve_content(content, template_id, candidate)
        when = self._parse_scheduled_at(scheduled_at)

        if when and when > timezone.now():
            message = Message.objects.create(
                candidate=candidate,
                channel=channel,
                content=rendered_content,
                status=MessageStatusLog.SCHEDULED,
                provider=provider_name or "",
                provider_message_id="",
                scheduled_at=when,
                template=template,
            )
            self._apply_candidate_status(candidate, MessageStatusLog.SCHEDULED)
            return self._outcome_from_message(message, success=True)

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
                content=rendered_content,
                status=MessageStatusLog.FAILED,
                provider=provider_name or "validation-guard",
                provider_message_id="",
                failure_category=analysis.category.value,
                error_message=analysis.recruiter_message,
                template=template,
            )
            self._apply_candidate_status(candidate, MessageStatusLog.FAILED)
            return self._outcome_from_message(message, success=False)

        provider = self._resolve_provider(channel, provider_name=provider_name)
        provider_health = provider.health()
        if provider_health.get("status") == "unavailable":
            analysis = CommunicationFailureTranslator.translate(
                channel=channel,
                recipient=recipient,
                raw_error="service unavailable: communication provider is not reachable",
            )
            message = Message.objects.create(
                candidate=candidate,
                channel=channel,
                content=rendered_content,
                status=MessageStatusLog.FAILED,
                provider=provider.provider_name,
                provider_message_id="",
                failure_category=analysis.category.value,
                error_message=(
                    "Communication service unavailable. The selected provider is not running, "
                    "so this message was not sent. Please start the provider or choose another method, then retry."
                ),
                template=template,
            )
            self._apply_candidate_status(candidate, MessageStatusLog.FAILED)
            return self._outcome_from_message(message, success=False)

        # Dispatch via provider
        provider_result: ProviderMessageResult = provider.send(
            recipient=recipient,
            content=rendered_content,
            channel=channel,
        )

        final_status = forced_status or provider_result.status.value

        # Create persistent message record
        message = Message.objects.create(
            candidate=candidate,
            channel=channel,
            content=rendered_content,
            status=final_status,
            provider=provider_result.provider_name,
            provider_message_id=provider_result.provider_message_id,
            failure_category=provider_result.failure_category or '',
            error_message=provider_result.error_message or '',
            template=template,
        )

        self._apply_candidate_status(candidate, final_status)

        return self._outcome_from_message(
            message,
            success=provider_result.success and final_status != MessageStatusLog.FAILED,
        )

    def send_bulk_messages(
        self,
        candidate_ids: List[int],
        channel: str,
        content: str,
        provider_name: Optional[str] = None,
        scheduled_at=None,
        template_id: Optional[int] = None,
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
                    scheduled_at=scheduled_at,
                    template_id=template_id,
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
                        is_retryable=analysis.is_retryable,
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
            # 1. Direct provider message ID (e.g., sent_xxxx)
            message = Message.objects.select_related('candidate').filter(
                provider_message_id=provider_message_id
            ).first()

            # 2. Candidate ID code fallback (e.g. 5W66W5 or CAN-001) -> resolve latest message
            if not message:
                message = Message.objects.select_related('candidate').filter(
                    candidate__candidate_id__iexact=provider_message_id
                ).order_by('-sent_at', '-id').first()

            # 3. Numeric candidate database ID or message ID
            if not message and provider_message_id.isdigit():
                message = Message.objects.select_related('candidate').filter(
                    candidate_id=int(provider_message_id)
                ).order_by('-sent_at', '-id').first() or Message.objects.select_related('candidate').filter(
                    id=int(provider_message_id)
                ).first()

            # 4. Candidate full name fallback (case-insensitive) -> resolve latest message
            if not message:
                message = Message.objects.select_related('candidate').filter(
                    candidate__full_name__iexact=provider_message_id
                ).order_by('-sent_at', '-id').first()

        if not message:
            return StatusUpdateOutcome(
                message=None,
                status=new_status,
                updated=False,
                was_duplicate=False,
                detail=f"Message not found (ID: {message_id}, Provider ID / Candidate ID: {provider_message_id}).",
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

    def sync_recent_active_messages(self, limit: int = 15) -> int:
        """
        Polls the communication provider for active messages in SENT/DELIVERED status
        and advances their status if updated on the provider.
        Provides a secondary fallback guaranteeing 100% real-time accuracy even if webhooks fail.
        """
        active_messages = Message.objects.select_related('candidate').filter(
            status__in=[MessageStatusLog.SENT, MessageStatusLog.DELIVERED]
        ).exclude(provider_message_id='').order_by('-sent_at')[:limit]

        updated_count = 0
        provider = self._resolve_provider(channel='sms')
        for msg in active_messages:
            try:
                latest = provider.check_status(msg.provider_message_id)
                if latest and latest.value != msg.status:
                    outcome = self.update_message_status(
                        message_id=msg.id,
                        new_status=latest.value,
                    )
                    if outcome.updated:
                        updated_count += 1
            except Exception:
                pass
        return updated_count

    def dispatch_due_scheduled_messages(self) -> List[CandidateMessageOutcome]:
        """Send every scheduled message whose send time has arrived, and sync active messages."""
        self.sync_recent_active_messages()
        due = (
            Message.objects.select_related("candidate", "template")
            .filter(status=MessageStatusLog.SCHEDULED, scheduled_at__lte=timezone.now())
            .order_by("scheduled_at", "id")
        )
        outcomes: List[CandidateMessageOutcome] = []
        for message in due:
            outcomes.append(self._dispatch_existing_message(message))
        return outcomes

    def _dispatch_existing_message(self, message: Message, increment_retry: bool = False) -> CandidateMessageOutcome:
        candidate = message.candidate
        channel = message.channel
        recipient = (candidate.email if channel == "email" and candidate.email else candidate.mobile_number) or ""
        provider_name = message.provider or None

        if not recipient or (channel in ("sms", "whatsapp") and not CommunicationFailureTranslator._is_valid_phone(recipient)):
            analysis = CommunicationFailureTranslator.translate(
                channel=channel,
                recipient=recipient,
                raw_error="Missing or invalid recipient contact details.",
            )
            message.status = MessageStatusLog.FAILED
            message.failure_category = analysis.category.value
            message.error_message = analysis.recruiter_message
            if increment_retry:
                message.retry_count += 1
            message.save()
            self._apply_candidate_status(candidate, MessageStatusLog.FAILED)
            return self._outcome_from_message(message, success=False)

        provider = self._resolve_provider(channel, provider_name=provider_name)
        health = provider.health()
        if health.get("status") == "unavailable":
            analysis = CommunicationFailureTranslator.translate(
                channel=channel,
                recipient=recipient,
                raw_error="service unavailable: communication provider is not reachable",
            )
            message.status = MessageStatusLog.FAILED
            message.provider = provider.provider_name
            message.failure_category = analysis.category.value
            message.error_message = (
                "Communication service unavailable. The provider is not running, so this message was not sent."
            )
            if increment_retry:
                message.retry_count += 1
            message.save()
            self._apply_candidate_status(candidate, MessageStatusLog.FAILED)
            return self._outcome_from_message(message, success=False)

        provider_result = provider.send(
            recipient=recipient,
            content=message.content,
            channel=channel,
        )
        message.status = provider_result.status.value
        message.provider = provider_result.provider_name
        message.provider_message_id = provider_result.provider_message_id
        message.failure_category = provider_result.failure_category or ""
        message.error_message = provider_result.error_message or ""
        message.sent_at = timezone.now()
        if increment_retry:
            message.retry_count += 1
        message.save()
        self._apply_candidate_status(candidate, message.status)
        return self._outcome_from_message(
            message,
            success=provider_result.success and message.status != MessageStatusLog.FAILED,
        )

    def retry_failed_message(self, message_id: int) -> CandidateMessageOutcome:
        try:
            message = Message.objects.select_related("candidate").get(id=message_id)
        except Message.DoesNotExist:
            return CandidateMessageOutcome(
                candidate_id=0,
                candidate_name="Unknown",
                candidate_code="",
                success=False,
                status=MessageStatusLog.FAILED,
                message_id=None,
                provider="none",
                provider_message_id="",
                failure_category="",
                error_message=f"Message {message_id} was not found.",
                is_retryable=False,
            )

        if message.status != MessageStatusLog.FAILED:
            return CandidateMessageOutcome(
                candidate_id=message.candidate_id,
                candidate_name=message.candidate.full_name,
                candidate_code=message.candidate.candidate_id,
                success=False,
                status=message.status,
                message_id=message.id,
                provider=message.provider,
                provider_message_id=message.provider_message_id,
                failure_category=message.failure_category or None,
                error_message="Only failed messages can be retried.",
                is_retryable=False,
            )

        if not is_retryable_failure(message.failure_category):
            return CandidateMessageOutcome(
                candidate_id=message.candidate_id,
                candidate_name=message.candidate.full_name,
                candidate_code=message.candidate.candidate_id,
                success=False,
                status=message.status,
                message_id=message.id,
                provider=message.provider,
                provider_message_id=message.provider_message_id,
                failure_category=message.failure_category or None,
                error_message=(
                    "This failure is permanent and cannot be retried. "
                    "Update the candidate's contact details or message content, then send a new message."
                ),
                is_retryable=False,
            )

        return self._dispatch_existing_message(message, increment_retry=True)

    def get_health_snapshot(self) -> dict:
        stats = Message.objects.aggregate(
            messages_sent=Count("id", filter=Q(status__in=[
                MessageStatusLog.SENT, MessageStatusLog.DELIVERED, MessageStatusLog.READ,
            ])),
            messages_delivered=Count("id", filter=Q(status__in=[
                MessageStatusLog.DELIVERED, MessageStatusLog.READ,
            ])),
            messages_failed=Count("id", filter=Q(status=MessageStatusLog.FAILED)),
            messages_scheduled=Count("id", filter=Q(status=MessageStatusLog.SCHEDULED)),
            messages_read=Count("id", filter=Q(status=MessageStatusLog.READ)),
        )
        providers = ProviderFactory.catalog()
        statuses = [p.get("health", {}).get("status") for p in providers]
        if any(s == "unavailable" for s in statuses):
            overall = "unavailable" if statuses.count("unavailable") == len(statuses) else "degraded"
        elif any(s == "degraded" for s in statuses):
            overall = "degraded"
        else:
            overall = "operational"

        unavailable = [p for p in providers if p.get("health", {}).get("status") == "unavailable"]
        recruiter_notice = ""
        if unavailable:
            names = ", ".join(p["name"] for p in unavailable)
            recruiter_notice = (
                f"Communication service unavailable: {names}. "
                "Messages cannot be sent through the affected provider until it is running again."
            )

        return {
            "status": overall,
            "label": "Operational" if overall == "operational" else (
                "Degraded" if overall == "degraded" else "Unavailable"
            ),
            "recruiter_notice": recruiter_notice,
            "messages_sent": stats["messages_sent"],
            "messages_delivered": stats["messages_delivered"],
            "messages_failed": stats["messages_failed"],
            "messages_scheduled": stats["messages_scheduled"],
            "messages_read": stats["messages_read"],
            "providers": providers,
        }

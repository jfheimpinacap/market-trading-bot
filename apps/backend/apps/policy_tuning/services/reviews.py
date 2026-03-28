from __future__ import annotations

from django.db import transaction

from apps.approval_center.models import ApprovalRequestStatus
from apps.approval_center.services import apply_decision
from apps.policy_tuning.models import PolicyTuningCandidate, PolicyTuningCandidateStatus, PolicyTuningReview


@transaction.atomic
def review_candidate(*, candidate: PolicyTuningCandidate, decision: str, reviewer_note: str = '', metadata: dict | None = None) -> PolicyTuningCandidate:
    PolicyTuningReview.objects.create(
        candidate=candidate,
        decision=decision,
        reviewer_note=reviewer_note,
        metadata=metadata or {},
    )

    if decision == 'APPROVE':
        candidate.status = PolicyTuningCandidateStatus.APPROVED
    elif decision == 'REJECT':
        candidate.status = PolicyTuningCandidateStatus.REJECTED
    else:
        candidate.status = PolicyTuningCandidateStatus.PENDING_APPROVAL

    if candidate.approval_request:
        if candidate.approval_request.status != ApprovalRequestStatus.PENDING and decision in {'APPROVE', 'REJECT'}:
            candidate.approval_request.status = ApprovalRequestStatus.PENDING
            candidate.approval_request.decided_at = None
            candidate.approval_request.save(update_fields=['status', 'decided_at', 'updated_at'])

        if decision == 'APPROVE':
            apply_decision(approval=candidate.approval_request, decision='APPROVE', rationale=reviewer_note, metadata={'policy_tuning': True})
        elif decision == 'REJECT':
            apply_decision(approval=candidate.approval_request, decision='REJECT', rationale=reviewer_note, metadata={'policy_tuning': True})
        elif candidate.approval_request.status != ApprovalRequestStatus.PENDING:
            candidate.approval_request.status = ApprovalRequestStatus.PENDING
            candidate.approval_request.decided_at = None
            candidate.approval_request.save(update_fields=['status', 'decided_at', 'updated_at'])

    candidate.metadata = {
        **(candidate.metadata or {}),
        'latest_review_decision': decision,
    }
    candidate.save(update_fields=['status', 'metadata', 'updated_at'])
    return candidate

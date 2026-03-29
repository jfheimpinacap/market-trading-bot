from __future__ import annotations

from dataclasses import dataclass

from apps.approval_center.models import ApprovalRequestStatus
from apps.autonomy_feedback.models import DownstreamStatus, ResolutionStatus, ResolutionType
from apps.autonomy_followup.models import CampaignFollowup, FollowupType


@dataclass(slots=True)
class DownstreamEvaluation:
    downstream_status: str
    resolution_status: str
    resolution_type: str
    rationale: str
    reason_codes: list[str]
    blockers: list[str]


def evaluate_downstream(followup: CampaignFollowup) -> DownstreamEvaluation:
    if followup.followup_type == FollowupType.MEMORY_INDEX:
        if followup.linked_memory_document_id:
            return DownstreamEvaluation(
                downstream_status=DownstreamStatus.COMPLETED,
                resolution_status=ResolutionStatus.COMPLETED,
                resolution_type=ResolutionType.MEMORY_RESOLVED,
                rationale='Memory document is linked to the emitted follow-up.',
                reason_codes=['memory_document_linked'],
                blockers=[],
            )
        return DownstreamEvaluation(
            downstream_status=DownstreamStatus.PENDING,
            resolution_status=ResolutionStatus.PENDING,
            resolution_type=ResolutionType.MANUAL_REVIEW_REQUIRED,
            rationale='Memory follow-up is emitted but no linked memory document is available yet.',
            reason_codes=['memory_document_missing'],
            blockers=['await_memory_document'],
        )

    if followup.followup_type == FollowupType.POSTMORTEM_REQUEST:
        request = followup.linked_postmortem_request
        if not request:
            return DownstreamEvaluation(
                downstream_status=DownstreamStatus.PENDING,
                resolution_status=ResolutionStatus.PENDING,
                resolution_type=ResolutionType.MANUAL_REVIEW_REQUIRED,
                rationale='Postmortem follow-up has no linked approval request yet.',
                reason_codes=['postmortem_request_missing'],
                blockers=['await_postmortem_request'],
            )
        if request.status == ApprovalRequestStatus.APPROVED:
            return DownstreamEvaluation(
                downstream_status=DownstreamStatus.COMPLETED,
                resolution_status=ResolutionStatus.COMPLETED,
                resolution_type=ResolutionType.POSTMORTEM_RESOLVED,
                rationale='Postmortem request was approved and can be considered resolved.',
                reason_codes=['postmortem_request_approved'],
                blockers=[],
            )
        if request.status in {ApprovalRequestStatus.REJECTED, ApprovalRequestStatus.CANCELLED, ApprovalRequestStatus.EXPIRED}:
            return DownstreamEvaluation(
                downstream_status=DownstreamStatus.REJECTED,
                resolution_status=ResolutionStatus.REJECTED,
                resolution_type=ResolutionType.MANUAL_REVIEW_REQUIRED,
                rationale='Postmortem request was rejected/cancelled and requires operator follow-up.',
                reason_codes=['postmortem_request_rejected'],
                blockers=['postmortem_request_rejected'],
            )
        if request.status == ApprovalRequestStatus.ESCALATED:
            return DownstreamEvaluation(
                downstream_status=DownstreamStatus.BLOCKED,
                resolution_status=ResolutionStatus.BLOCKED,
                resolution_type=ResolutionType.MANUAL_REVIEW_REQUIRED,
                rationale='Postmortem request is escalated and blocked on manual handling.',
                reason_codes=['postmortem_request_escalated'],
                blockers=['postmortem_escalated'],
            )
        return DownstreamEvaluation(
            downstream_status=DownstreamStatus.PENDING,
            resolution_status=ResolutionStatus.PENDING,
            resolution_type=ResolutionType.MANUAL_REVIEW_REQUIRED,
            rationale='Postmortem request is still pending approval workflow.',
            reason_codes=['postmortem_request_pending'],
            blockers=['await_postmortem_approval'],
        )

    review_state = (followup.metadata or {}).get('feedback_review_status', '')
    if review_state in {'REVIEWED', 'COMPLETED'}:
        return DownstreamEvaluation(
            downstream_status=DownstreamStatus.COMPLETED,
            resolution_status=ResolutionStatus.COMPLETED,
            resolution_type=ResolutionType.ROADMAP_FEEDBACK_REVIEWED,
            rationale='Roadmap/scenario feedback artifact is marked as reviewed.',
            reason_codes=['feedback_reviewed'],
            blockers=[],
        )
    if followup.linked_feedback_artifact:
        return DownstreamEvaluation(
            downstream_status=DownstreamStatus.IN_PROGRESS,
            resolution_status=ResolutionStatus.IN_PROGRESS,
            resolution_type=ResolutionType.MANUAL_REVIEW_REQUIRED,
            rationale='Feedback artifact exists, but no explicit review confirmation was found.',
            reason_codes=['feedback_artifact_unreviewed'],
            blockers=['await_feedback_review_confirmation'],
        )
    return DownstreamEvaluation(
        downstream_status=DownstreamStatus.UNKNOWN,
        resolution_status=ResolutionStatus.PENDING,
        resolution_type=ResolutionType.MANUAL_REVIEW_REQUIRED,
        rationale='No linked feedback artifact exists for the emitted roadmap follow-up.',
        reason_codes=['feedback_artifact_missing'],
        blockers=['await_feedback_artifact'],
    )

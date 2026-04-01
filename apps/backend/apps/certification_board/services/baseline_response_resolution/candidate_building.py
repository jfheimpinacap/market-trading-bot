from __future__ import annotations

from apps.certification_board.models import (
    BaselineResponseCase,
    DownstreamLifecycleOutcomeType,
    ResponseResolutionCandidate,
    ResponseResolutionProgressStatus,
    ResponseRoutingAction,
)


def _progress_from_outcome(outcome_type: str | None) -> tuple[str, bool, list[str]]:
    if not outcome_type:
        return ResponseResolutionProgressStatus.UNKNOWN, False, ['missing_lifecycle_outcome']
    if outcome_type == DownstreamLifecycleOutcomeType.WAITING_EVIDENCE:
        return ResponseResolutionProgressStatus.WAITING_EVIDENCE, False, ['waiting_evidence']
    if outcome_type == DownstreamLifecycleOutcomeType.STILL_UNDER_REVIEW:
        return ResponseResolutionProgressStatus.IN_PROGRESS, False, ['still_under_review']
    if outcome_type == DownstreamLifecycleOutcomeType.ESCALATED_BACK:
        return ResponseResolutionProgressStatus.FOLLOWUP_REQUIRED, False, ['escalated_back']
    if outcome_type in {
        DownstreamLifecycleOutcomeType.RESOLVED_BY_TARGET,
        DownstreamLifecycleOutcomeType.REJECTED_BY_TARGET,
        DownstreamLifecycleOutcomeType.NO_ACTION_TAKEN,
    }:
        return ResponseResolutionProgressStatus.READY_TO_RESOLVE, True, []
    return ResponseResolutionProgressStatus.UNKNOWN, False, ['unknown_outcome_type']


def build_resolution_candidate(*, run, response_case: BaselineResponseCase) -> ResponseResolutionCandidate:
    latest_tracking = response_case.tracking_records.order_by('-created_at', '-id').first()
    latest_ack = response_case.downstream_acknowledgements.order_by('-created_at', '-id').first()
    latest_outcome = response_case.downstream_lifecycle_outcomes.order_by('-created_at', '-id').first()
    latest_action = ResponseRoutingAction.objects.filter(linked_response_case=response_case).order_by('-created_at', '-id').first()

    progress, ready_for_resolution, blockers = _progress_from_outcome(getattr(latest_outcome, 'outcome_type', None))
    if latest_outcome is None and latest_ack is not None:
        progress = ResponseResolutionProgressStatus.IN_PROGRESS
        blockers = ['missing_lifecycle_outcome']

    return ResponseResolutionCandidate.objects.create(
        resolution_run=run,
        linked_response_case=response_case,
        linked_routing_action=latest_action,
        latest_tracking_record=latest_tracking,
        latest_acknowledgement=latest_ack,
        latest_lifecycle_outcome=latest_outcome,
        target_component=response_case.target_component,
        target_scope=response_case.target_scope,
        downstream_progress_status=progress,
        ready_for_resolution=ready_for_resolution,
        blockers=blockers,
        metadata={'source': 'baseline-response-resolution-run'},
    )

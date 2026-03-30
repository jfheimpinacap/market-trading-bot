from __future__ import annotations

from apps.certification_board.models import (
    BaselineResponseCase,
    DownstreamAcknowledgement,
    DownstreamAcknowledgementStatus,
    DownstreamLifecycleOutcome,
    DownstreamLifecycleOutcomeStatus,
    DownstreamLifecycleOutcomeType,
    ResponseReviewStageRecord,
    ResponseReviewStageType,
)


def derive_downstream_outcome(
    *,
    response_case: BaselineResponseCase,
    acknowledgement: DownstreamAcknowledgement | None,
    latest_stage: ResponseReviewStageRecord | None,
) -> tuple[str, str, str]:
    if acknowledgement and acknowledgement.acknowledgement_status == DownstreamAcknowledgementStatus.REJECTED_BY_TARGET:
        return DownstreamLifecycleOutcomeType.REJECTED_BY_TARGET, DownstreamLifecycleOutcomeStatus.CONFIRMED, 'Downstream destination rejected the routed response case.'
    if acknowledgement and acknowledgement.acknowledgement_status == DownstreamAcknowledgementStatus.WAITING_MORE_EVIDENCE:
        return DownstreamLifecycleOutcomeType.WAITING_EVIDENCE, DownstreamLifecycleOutcomeStatus.DEFERRED, 'Downstream destination requested additional evidence before committee conclusion.'
    if latest_stage and latest_stage.stage_type == ResponseReviewStageType.DOWNSTREAM_RESOLUTION:
        return DownstreamLifecycleOutcomeType.RESOLVED_BY_TARGET, DownstreamLifecycleOutcomeStatus.CONFIRMED, 'Downstream review reached a resolution stage and is ready for manual case resolution.'
    if acknowledgement and acknowledgement.acknowledgement_status in {DownstreamAcknowledgementStatus.ACKNOWLEDGED, DownstreamAcknowledgementStatus.ACCEPTED_FOR_REVIEW}:
        return DownstreamLifecycleOutcomeType.STILL_UNDER_REVIEW, DownstreamLifecycleOutcomeStatus.PROPOSED, 'Case is acknowledged downstream and remains under active review.'
    if acknowledgement and acknowledgement.acknowledgement_status == DownstreamAcknowledgementStatus.NO_RESPONSE:
        return DownstreamLifecycleOutcomeType.ESCALATED_BACK, DownstreamLifecycleOutcomeStatus.BLOCKED, 'No downstream response recorded; manual follow-up escalation is recommended.'
    return DownstreamLifecycleOutcomeType.NO_ACTION_TAKEN, DownstreamLifecycleOutcomeStatus.PROPOSED, 'Case is routed but has no confirmed downstream lifecycle progression yet.'


def record_or_update_outcome(
    *,
    response_case: BaselineResponseCase,
    acknowledgement: DownstreamAcknowledgement | None,
    latest_stage: ResponseReviewStageRecord | None,
    outcome_type: str | None = None,
    outcome_status: str | None = None,
    outcome_rationale: str | None = None,
    linked_target_reference: str = '',
    metadata: dict | None = None,
) -> DownstreamLifecycleOutcome:
    if not (outcome_type and outcome_status and outcome_rationale):
        derived_type, derived_status, derived_rationale = derive_downstream_outcome(response_case=response_case, acknowledgement=acknowledgement, latest_stage=latest_stage)
    else:
        derived_type, derived_status, derived_rationale = outcome_type, outcome_status, outcome_rationale
    outcome, _ = DownstreamLifecycleOutcome.objects.update_or_create(
        linked_response_case=response_case,
        defaults={
            'linked_acknowledgement': acknowledgement,
            'linked_latest_stage': latest_stage,
            'outcome_type': derived_type,
            'outcome_status': derived_status,
            'outcome_rationale': derived_rationale,
            'linked_target_reference': linked_target_reference,
            'metadata': metadata or {},
        },
    )
    return outcome

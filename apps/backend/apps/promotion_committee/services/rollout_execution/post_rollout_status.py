from __future__ import annotations

from apps.promotion_committee.models import (
    CheckpointOutcomeRecord,
    CheckpointOutcomeStatus,
    CheckpointTriggeredAction,
    PostRolloutStatus,
    PostRolloutStatusType,
    RolloutExecutionRecord,
    RolloutExecutionStatus,
)
from apps.promotion_committee.services.rollout_execution.signals import collect_post_rollout_flags


def consolidate_post_rollout_status(*, execution: RolloutExecutionRecord) -> PostRolloutStatus:
    outcomes = list(CheckpointOutcomeRecord.objects.filter(linked_rollout_execution=execution).order_by('-created_at', '-id'))
    flags = collect_post_rollout_flags(plan=execution.linked_rollout_plan)

    if execution.execution_status == RolloutExecutionStatus.REVERTED:
        status = PostRolloutStatusType.REVERTED
        rationale = 'Execution already reverted manually; rollout is no longer active.'
    elif any(item.triggered_action == CheckpointTriggeredAction.RECOMMEND_ROLLBACK for item in outcomes):
        status = PostRolloutStatusType.ROLLBACK_RECOMMENDED
        rationale = 'Critical checkpoint recommended manual rollback.'
    elif any(item.outcome_status == CheckpointOutcomeStatus.FAILED for item in outcomes):
        status = PostRolloutStatusType.REVIEW_REQUIRED
        rationale = 'At least one checkpoint failed and requires manual review.'
    elif any(item.outcome_status == CheckpointOutcomeStatus.WARNING for item in outcomes):
        status = PostRolloutStatusType.CAUTION
        rationale = 'Checkpoint warning observed; continue only with bounded observation.'
    elif outcomes and all(item.outcome_status == CheckpointOutcomeStatus.PASSED for item in outcomes):
        status = PostRolloutStatusType.HEALTHY
        rationale = 'All recorded outcomes passed with no critical flags.'
    else:
        status = PostRolloutStatusType.INCOMPLETE
        rationale = 'No sufficient checkpoint outcomes recorded yet.'

    return PostRolloutStatus.objects.create(
        linked_rollout_execution=execution,
        status=status,
        status_rationale=rationale,
        linked_checkpoint_outcomes=[item.id for item in outcomes],
        observed_drift_flags=list(flags.get('drift_flags') or []),
        observed_risk_flags=list(flags.get('risk_flags') or []),
        observed_calibration_flags=list(flags.get('calibration_flags') or []),
        metadata={'linked_context': flags.get('linked_context') or {}, 'manual_only': True},
    )

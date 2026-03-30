from __future__ import annotations

from django.utils import timezone

from apps.promotion_committee.models import (
    CheckpointOutcomeRecord,
    CheckpointOutcomeStatus,
    CheckpointTriggeredAction,
    RolloutCheckpointPlan,
    RolloutCheckpointStatus,
    RolloutExecutionRecord,
    RolloutExecutionStatus,
)


def record_checkpoint_outcome(
    *,
    checkpoint_plan: RolloutCheckpointPlan,
    outcome_status: str,
    observed_metrics: dict | None = None,
    rationale: str,
    actor: str = 'operator',
    metadata: dict | None = None,
) -> CheckpointOutcomeRecord:
    execution = checkpoint_plan.linked_rollout_plan.execution_record
    normalized = (outcome_status or '').upper()

    if normalized == CheckpointOutcomeStatus.FAILED:
        triggered_action = (
            CheckpointTriggeredAction.RECOMMEND_ROLLBACK if checkpoint_plan.checkpoint_type == 'rollback_readiness_check' else CheckpointTriggeredAction.REQUIRE_REVIEW
        )
        checkpoint_plan.checkpoint_status = RolloutCheckpointStatus.FAILED
    elif normalized == CheckpointOutcomeStatus.WARNING:
        triggered_action = CheckpointTriggeredAction.PAUSE
        checkpoint_plan.checkpoint_status = RolloutCheckpointStatus.PLANNED
    elif normalized == CheckpointOutcomeStatus.SKIPPED:
        triggered_action = CheckpointTriggeredAction.REQUIRE_REVIEW
        checkpoint_plan.checkpoint_status = RolloutCheckpointStatus.SKIPPED
    else:
        normalized = CheckpointOutcomeStatus.PASSED
        triggered_action = CheckpointTriggeredAction.CONTINUE
        checkpoint_plan.checkpoint_status = RolloutCheckpointStatus.PASSED

    checkpoint_plan.save(update_fields=['checkpoint_status', 'updated_at'])

    outcome = CheckpointOutcomeRecord.objects.create(
        linked_rollout_execution=execution,
        linked_checkpoint_plan=checkpoint_plan,
        outcome_status=normalized,
        observed_metrics=observed_metrics or {},
        outcome_rationale=rationale,
        triggered_action=triggered_action,
        recorded_by=actor,
        recorded_at=timezone.now(),
        metadata=metadata or {},
    )

    if triggered_action == CheckpointTriggeredAction.PAUSE:
        execution.execution_status = RolloutExecutionStatus.PAUSED
    elif triggered_action == CheckpointTriggeredAction.RECOMMEND_ROLLBACK:
        execution.execution_status = RolloutExecutionStatus.ROLLBACK_RECOMMENDED
    elif triggered_action == CheckpointTriggeredAction.REQUIRE_REVIEW and execution.execution_status == RolloutExecutionStatus.EXECUTED:
        execution.execution_status = RolloutExecutionStatus.PAUSED
    execution.save(update_fields=['execution_status', 'updated_at'])
    return outcome


def get_execution_for_checkpoint(*, checkpoint_id: int) -> RolloutExecutionRecord:
    checkpoint_plan = RolloutCheckpointPlan.objects.select_related('linked_rollout_plan__execution_record').get(pk=checkpoint_id)
    return checkpoint_plan.linked_rollout_plan.execution_record

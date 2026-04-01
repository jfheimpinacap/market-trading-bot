from __future__ import annotations

from apps.mission_control.models import (
    AutonomousMissionCycleExecution,
    AutonomousMissionCycleOutcome,
    AutonomousMissionCycleOutcomeStatus,
)


def build_cycle_outcome(*, cycle_execution: AutonomousMissionCycleExecution) -> AutonomousMissionCycleOutcome:
    metadata = cycle_execution.metadata or {}
    dispatch_count = 0
    close_action_count = 0
    watch_update_count = 1 if cycle_execution.linked_position_watch_run else 0

    if cycle_execution.linked_execution_intake_run:
        dispatch_count = 1
    if metadata.get('mission_cycle_status') == 'PARTIAL':
        close_action_count = 1

    postmortem_count = 1 if close_action_count else 0
    learning_count = 1 if close_action_count else 0
    reuse_count = 1 if cycle_execution.linked_feedback_reuse_run else 0

    if cycle_execution.execution_status == 'BLOCKED':
        outcome_status = AutonomousMissionCycleOutcomeStatus.BLOCKED
    elif dispatch_count > 0:
        outcome_status = AutonomousMissionCycleOutcomeStatus.EXECUTION_OCCURRED
    elif watch_update_count > 0:
        outcome_status = AutonomousMissionCycleOutcomeStatus.WATCH_ONLY
    else:
        outcome_status = AutonomousMissionCycleOutcomeStatus.NO_ACTION

    return AutonomousMissionCycleOutcome.objects.create(
        linked_cycle_execution=cycle_execution,
        outcome_status=outcome_status,
        dispatch_count=dispatch_count,
        watch_update_count=watch_update_count,
        close_action_count=close_action_count,
        postmortem_count=postmortem_count,
        learning_count=learning_count,
        reuse_count=reuse_count,
        outcome_summary=f'Outcome={outcome_status}, dispatch={dispatch_count}, watch={watch_update_count}, learning={learning_count}.',
        metadata={'source_execution_status': cycle_execution.execution_status},
    )

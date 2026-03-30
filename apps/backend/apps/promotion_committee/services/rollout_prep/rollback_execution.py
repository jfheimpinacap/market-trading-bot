from __future__ import annotations

from django.utils import timezone

from apps.promotion_committee.models import (
    AdoptionRollbackPlan,
    AdoptionRollbackStatus,
    ManualAdoptionAction,
    ManualRollbackExecution,
    ManualRollbackExecutionStatus,
    ManualRolloutPlan,
)


def prepare_manual_rollback_execution(*, action: ManualAdoptionAction, plan: ManualRolloutPlan | None = None) -> ManualRollbackExecution:
    rollback_plan = AdoptionRollbackPlan.objects.filter(linked_manual_action=action).first()
    blockers = []
    status = ManualRollbackExecutionStatus.READY
    if rollback_plan is None:
        blockers.append('rollback_plan_missing')
        status = ManualRollbackExecutionStatus.BLOCKED

    execution, _ = ManualRollbackExecution.objects.update_or_create(
        linked_manual_action=action,
        defaults={
            'linked_rollout_plan': plan,
            'linked_rollback_plan': rollback_plan,
            'execution_status': status,
            'rollback_type': rollback_plan.rollback_type if rollback_plan else 'RETURN_TO_BASELINE',
            'rollback_target_snapshot': rollback_plan.rollback_target_snapshot if rollback_plan else {},
            'rationale': 'Manual rollback execution prepared for auditable paper/demo reversal control.',
            'metadata': {'blockers': blockers, 'manual_only': True},
        },
    )
    return execution


def execute_manual_rollback(*, action: ManualAdoptionAction, actor: str = 'operator') -> ManualRollbackExecution:
    execution = ManualRollbackExecution.objects.filter(linked_manual_action=action).select_related('linked_rollback_plan').first()
    if execution is None:
        execution = prepare_manual_rollback_execution(action=action)
    if execution.execution_status == ManualRollbackExecutionStatus.BLOCKED:
        return execution

    execution.execution_status = ManualRollbackExecutionStatus.EXECUTED
    execution.executed_by = actor
    execution.executed_at = timezone.now()
    execution.save(update_fields=['execution_status', 'executed_by', 'executed_at', 'updated_at'])

    if execution.linked_rollback_plan:
        execution.linked_rollback_plan.rollback_status = AdoptionRollbackStatus.EXECUTED
        execution.linked_rollback_plan.save(update_fields=['rollback_status', 'updated_at'])

    action.action_status = 'ROLLBACK_AVAILABLE'
    action.save(update_fields=['action_status', 'updated_at'])
    return execution

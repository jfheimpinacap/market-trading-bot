from __future__ import annotations

from apps.promotion_committee.models import (
    AdoptionRollbackPlan,
    AdoptionRollbackStatus,
    AdoptionRollbackType,
    ManualAdoptionAction,
    ManualAdoptionActionType,
)


def prepare_rollback_plan(*, action: ManualAdoptionAction, force: bool = False):
    if action.action_type == ManualAdoptionActionType.PREPARE_ROLLOUT_PLAN:
        rollback_type = AdoptionRollbackType.CANCEL_ROLLOUT_PLAN
    elif action.action_type == ManualAdoptionActionType.APPLY_STACK_BINDING_CHANGE:
        rollback_type = AdoptionRollbackType.RESTORE_BINDING
    elif action.action_type in {
        ManualAdoptionActionType.APPLY_POLICY_TUNING_CHANGE,
        ManualAdoptionActionType.APPLY_TRUST_CALIBRATION_CHANGE,
    }:
        rollback_type = AdoptionRollbackType.REVERT_VALUE
    else:
        rollback_type = AdoptionRollbackType.RETURN_TO_BASELINE

    if rollback_type == AdoptionRollbackType.RETURN_TO_BASELINE and not force:
        return None

    plan, _ = AdoptionRollbackPlan.objects.update_or_create(
        linked_manual_action=action,
        defaults={
            'rollback_type': rollback_type,
            'rollback_status': AdoptionRollbackStatus.PREPARED,
            'rollback_target_snapshot': {
                'before': action.current_value_snapshot,
                'after': action.proposed_value_snapshot,
                'target_component': action.target_component,
                'target_scope': action.target_scope,
            },
            'rationale': 'Prepared rollback plan for explicit manual-first paper/demo adoption action.',
            'metadata': {'auto_executed': False, 'paper_only': True},
        },
    )
    return plan

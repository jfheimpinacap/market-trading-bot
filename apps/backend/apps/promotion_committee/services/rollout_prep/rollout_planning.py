from __future__ import annotations

from apps.promotion_committee.models import (
    ManualRolloutPlan,
    ManualRolloutPlanStatus,
    ManualAdoptionActionType,
    RolloutActionCandidate,
    RolloutNeedLevel,
    RolloutPlanType,
)


def _resolve_plan_type(candidate: RolloutActionCandidate) -> str:
    if candidate.action_type == ManualAdoptionActionType.APPLY_STACK_BINDING_CHANGE:
        return RolloutPlanType.STAGED_BINDING_ROLLOUT
    if candidate.action_type == ManualAdoptionActionType.APPLY_TRUST_CALIBRATION_CHANGE:
        return RolloutPlanType.TRUST_CALIBRATION_ROLLOUT
    if candidate.action_type == ManualAdoptionActionType.APPLY_POLICY_TUNING_CHANGE:
        return RolloutPlanType.POLICY_TUNING_ROLLOUT
    if candidate.rollout_need_level == RolloutNeedLevel.ROLLOUT_REQUIRED:
        return RolloutPlanType.SHADOW_CONFIG_ROLLOUT
    return RolloutPlanType.DIRECT_CONFIG_APPLY


def _default_stages(plan_type: str) -> list[dict]:
    if plan_type == RolloutPlanType.DIRECT_CONFIG_APPLY:
        return [
            {'step': 'pre_apply_review', 'manual': True},
            {'step': 'bounded_apply', 'manual': True},
            {'step': 'post_apply_observe', 'manual': True},
        ]
    return [
        {'step': 'paper_rollout_plan_review', 'manual': True},
        {'step': 'checkpoint_gate', 'manual': True},
        {'step': 'sandbox_rollout_execution', 'manual': True},
        {'step': 'post_rollout_monitoring', 'manual': True},
    ]


def plan_manual_rollout(*, candidate: RolloutActionCandidate) -> ManualRolloutPlan:
    plan_type = _resolve_plan_type(candidate)
    status = ManualRolloutPlanStatus.READY if candidate.ready_for_rollout else ManualRolloutPlanStatus.BLOCKED
    if candidate.linked_manual_adoption_action.action_status == 'APPLIED':
        status = ManualRolloutPlanStatus.ROLLBACK_AVAILABLE

    plan, _ = ManualRolloutPlan.objects.update_or_create(
        linked_manual_adoption_action=candidate.linked_manual_adoption_action,
        defaults={
            'linked_candidate': candidate,
            'rollout_plan_type': plan_type,
            'rollout_status': status,
            'target_component': candidate.target_component,
            'target_scope': candidate.target_scope,
            'rollout_rationale': 'Manual-first paper/demo rollout plan prepared from approved adoption action.',
            'staged_steps': _default_stages(plan_type),
            'monitoring_intent': {
                'evaluation_lab': True,
                'trace_explorer': True,
                'cockpit_visible': True,
                'auto_rollout': False,
            },
            'linked_rollout_artifact': candidate.linked_manual_adoption_action.linked_target_artifact,
            'metadata': {'rollout_manager_bridge': True, 'champion_challenger_context': True, 'manual_only': True},
        },
    )
    return plan

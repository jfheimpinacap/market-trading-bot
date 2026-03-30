from __future__ import annotations

from apps.promotion_committee.models import (
    AdoptionTargetResolutionStatus,
    ManualAdoptionAction,
    ManualAdoptionActionStatus,
    ManualAdoptionActionType,
    RolloutActionCandidate,
    RolloutNeedLevel,
    RolloutPreparationRun,
)


def _classify_need_level(action: ManualAdoptionAction) -> str:
    sensitive_scope = action.target_scope == 'global'
    sensitive_action = action.action_type in {
        ManualAdoptionActionType.APPLY_STACK_BINDING_CHANGE,
        ManualAdoptionActionType.PREPARE_ROLLOUT_PLAN,
    }
    if sensitive_scope or sensitive_action:
        return RolloutNeedLevel.ROLLOUT_REQUIRED
    if action.action_type in {
        ManualAdoptionActionType.APPLY_POLICY_TUNING_CHANGE,
        ManualAdoptionActionType.APPLY_TRUST_CALIBRATION_CHANGE,
    }:
        return RolloutNeedLevel.ROLLOUT_RECOMMENDED
    return RolloutNeedLevel.DIRECT_APPLY_OK


def build_rollout_candidates(*, preparation_run: RolloutPreparationRun) -> list[RolloutActionCandidate]:
    actions = (
        ManualAdoptionAction.objects.select_related('linked_promotion_case', 'linked_candidate')
        .filter(action_status__in=[ManualAdoptionActionStatus.READY_TO_APPLY, ManualAdoptionActionStatus.APPLIED, ManualAdoptionActionStatus.ROLLBACK_AVAILABLE])
        .order_by('-created_at', '-id')[:250]
    )

    created: list[RolloutActionCandidate] = []
    for action in actions:
        resolution_status = action.linked_candidate.target_resolution_status if action.linked_candidate_id else AdoptionTargetResolutionStatus.UNKNOWN
        blockers = list(action.blockers or [])
        if not action.current_value_snapshot or not action.proposed_value_snapshot:
            blockers.append('missing_snapshots')
        if resolution_status in {AdoptionTargetResolutionStatus.BLOCKED, AdoptionTargetResolutionStatus.UNKNOWN}:
            blockers.append('target_mapping_incomplete')

        ready = len(blockers) == 0 and action.action_status != ManualAdoptionActionStatus.APPLIED
        defaults = {
            'preparation_run': preparation_run,
            'linked_promotion_case': action.linked_promotion_case,
            'target_component': action.target_component,
            'target_scope': action.target_scope,
            'action_type': action.action_type,
            'current_value_snapshot': action.current_value_snapshot,
            'proposed_value_snapshot': action.proposed_value_snapshot,
            'rollout_need_level': _classify_need_level(action),
            'target_resolution_status': resolution_status,
            'ready_for_rollout': ready,
            'blockers': blockers,
            'metadata': {'linked_target_artifact': action.linked_target_artifact, 'manual_first': True, 'paper_only': True},
        }
        candidate, _ = RolloutActionCandidate.objects.update_or_create(linked_manual_adoption_action=action, defaults=defaults)
        created.append(candidate)

    return created

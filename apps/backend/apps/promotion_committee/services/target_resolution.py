from __future__ import annotations

from dataclasses import dataclass

from apps.promotion_committee.models import (
    AdoptionActionCandidate,
    AdoptionTargetResolutionStatus,
    ManualAdoptionActionType,
    PromotionTargetComponent,
    PromotionTargetScope,
)


@dataclass
class TargetResolution:
    status: str
    action_type: str
    ready_for_action: bool
    blockers: list[str]
    reason_codes: list[str]
    current_snapshot: dict
    proposed_snapshot: dict
    linked_target_artifact: str
    requires_rollback: bool


def resolve_target(candidate: AdoptionActionCandidate) -> TargetResolution:
    blockers = list(candidate.blockers or [])
    reason_codes: list[str] = []
    current_snapshot = {'value': candidate.current_value or None}
    proposed_snapshot = {'value': candidate.proposed_value or None}
    linked_target_artifact = ''
    requires_rollback = False

    if not candidate.current_value or not candidate.proposed_value:
        blockers.append('missing_before_after_snapshot')
        return TargetResolution(
            status=AdoptionTargetResolutionStatus.BLOCKED,
            action_type=ManualAdoptionActionType.REQUIRE_TARGET_MAPPING,
            ready_for_action=False,
            blockers=blockers,
            reason_codes=['missing_before_or_after'],
            current_snapshot=current_snapshot,
            proposed_snapshot=proposed_snapshot,
            linked_target_artifact=linked_target_artifact,
            requires_rollback=False,
        )

    if candidate.target_component == PromotionTargetComponent.CALIBRATION:
        reason_codes.append('mapped_to_trust_calibration')
        linked_target_artifact = 'trust_calibration'
        action_type = ManualAdoptionActionType.APPLY_TRUST_CALIBRATION_CHANGE
        requires_rollback = True
    elif candidate.change_type in {'threshold_update', 'risk_gate_update', 'size_cap_update'}:
        reason_codes.append('mapped_to_policy_tuning')
        linked_target_artifact = 'policy_tuning'
        action_type = ManualAdoptionActionType.APPLY_POLICY_TUNING_CHANGE
        requires_rollback = True
    elif candidate.target_component in {PromotionTargetComponent.PREDICTION, PromotionTargetComponent.RISK} and candidate.target_scope == PromotionTargetScope.GLOBAL:
        reason_codes.append('global_sensitive_scope')
        linked_target_artifact = 'rollout_manager'
        action_type = ManualAdoptionActionType.PREPARE_ROLLOUT_PLAN
        requires_rollback = True
    elif candidate.change_type in {'shortlist_update', 'review_rule_update'}:
        reason_codes.append('stack_binding_change')
        linked_target_artifact = 'champion_challenger_binding'
        action_type = ManualAdoptionActionType.APPLY_STACK_BINDING_CHANGE
        requires_rollback = True
    else:
        reason_codes.append('manual_record_only')
        action_type = ManualAdoptionActionType.RECORD_MANUAL_ADOPTION

    status = AdoptionTargetResolutionStatus.RESOLVED
    if blockers:
        status = AdoptionTargetResolutionStatus.PARTIAL
    ready_for_action = status in {AdoptionTargetResolutionStatus.RESOLVED, AdoptionTargetResolutionStatus.PARTIAL}

    return TargetResolution(
        status=status,
        action_type=action_type,
        ready_for_action=ready_for_action,
        blockers=blockers,
        reason_codes=reason_codes,
        current_snapshot=current_snapshot,
        proposed_snapshot=proposed_snapshot,
        linked_target_artifact=linked_target_artifact,
        requires_rollback=requires_rollback,
    )

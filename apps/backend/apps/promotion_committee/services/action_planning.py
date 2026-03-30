from __future__ import annotations

from apps.promotion_committee.models import (
    AdoptionActionCandidate,
    AdoptionTargetResolutionStatus,
    ManualAdoptionAction,
    ManualAdoptionActionStatus,
    PromotionAdoptionRun,
)
from apps.promotion_committee.services.target_resolution import resolve_target


def plan_manual_action(*, adoption_run: PromotionAdoptionRun, candidate: AdoptionActionCandidate) -> tuple[ManualAdoptionAction, bool]:
    resolution = resolve_target(candidate)

    candidate.target_resolution_status = resolution.status
    candidate.ready_for_action = resolution.ready_for_action
    candidate.blockers = resolution.blockers
    candidate.metadata = {**(candidate.metadata or {}), 'reason_codes': resolution.reason_codes}
    candidate.save(update_fields=['target_resolution_status', 'ready_for_action', 'blockers', 'metadata', 'updated_at'])

    if resolution.status == AdoptionTargetResolutionStatus.BLOCKED:
        status = ManualAdoptionActionStatus.BLOCKED
    elif resolution.action_type == 'PREPARE_ROLLOUT_PLAN':
        status = ManualAdoptionActionStatus.PROPOSED
    else:
        status = ManualAdoptionActionStatus.READY_TO_APPLY

    action = (
        ManualAdoptionAction.objects.filter(
            linked_promotion_case=candidate.linked_promotion_case,
            action_type=resolution.action_type,
            action_status__in=[
                ManualAdoptionActionStatus.PROPOSED,
                ManualAdoptionActionStatus.READY_TO_APPLY,
                ManualAdoptionActionStatus.APPLIED,
                ManualAdoptionActionStatus.ROLLBACK_AVAILABLE,
            ],
        )
        .order_by('-created_at', '-id')
        .first()
    )

    created = False
    if action is None:
        action = ManualAdoptionAction.objects.create(
            linked_promotion_case=candidate.linked_promotion_case,
            linked_candidate=candidate,
            adoption_run=adoption_run,
            action_type=resolution.action_type,
            action_status=status,
            target_component=candidate.target_component,
            target_scope=candidate.target_scope,
            current_value_snapshot=resolution.current_snapshot,
            proposed_value_snapshot=resolution.proposed_snapshot,
            rationale=f'Manual adoption action prepared from approved promotion case #{candidate.linked_promotion_case_id}.',
            reason_codes=resolution.reason_codes,
            blockers=resolution.blockers,
            linked_target_artifact=resolution.linked_target_artifact,
            metadata={'manual_first': True, 'auto_apply': False, 'paper_only': True},
        )
        created = True
    else:
        action.linked_candidate = candidate
        action.adoption_run = adoption_run
        action.action_status = status if action.action_status != ManualAdoptionActionStatus.APPLIED else action.action_status
        action.current_value_snapshot = resolution.current_snapshot
        action.proposed_value_snapshot = resolution.proposed_snapshot
        action.reason_codes = resolution.reason_codes
        action.blockers = resolution.blockers
        action.linked_target_artifact = resolution.linked_target_artifact
        action.metadata = {**(action.metadata or {}), 'refreshed_by_run': adoption_run.id}
        action.save(
            update_fields=[
                'linked_candidate',
                'adoption_run',
                'action_status',
                'current_value_snapshot',
                'proposed_value_snapshot',
                'reason_codes',
                'blockers',
                'linked_target_artifact',
                'metadata',
                'updated_at',
            ]
        )

    return action, resolution.requires_rollback

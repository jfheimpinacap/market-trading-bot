from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.approval_center.models import ApprovalPriority, ApprovalRequest, ApprovalRequestStatus, ApprovalSourceType
from apps.automation_policy.models import AutomationPolicyRule, AutomationTrustTier
from apps.autonomy_manager.models import (
    AutonomyDomainStatus,
    AutonomyRecommendationCode,
    AutonomyStage,
    AutonomyStageRecommendation,
    AutonomyStageState,
    AutonomyStageTransition,
    AutonomyTransitionStatus,
)

TIER_BY_STAGE = {
    AutonomyStage.MANUAL: AutomationTrustTier.MANUAL_ONLY,
    AutonomyStage.ASSISTED: AutomationTrustTier.APPROVAL_REQUIRED,
    AutonomyStage.SUPERVISED_AUTOPILOT: AutomationTrustTier.SAFE_AUTOMATION,
    AutonomyStage.FROZEN: AutomationTrustTier.AUTO_BLOCKED,
    AutonomyStage.ROLLBACK_RECOMMENDED: AutomationTrustTier.MANUAL_ONLY,
}


def _requires_explicit_approval(recommendation: AutonomyStageRecommendation) -> bool:
    return recommendation.recommendation_code in {
        AutonomyRecommendationCode.PROMOTE_TO_SUPERVISED_AUTOPILOT,
        AutonomyRecommendationCode.FREEZE_DOMAIN,
        AutonomyRecommendationCode.ROLLBACK_STAGE,
    }


def _build_approval_request(transition: AutonomyStageTransition) -> ApprovalRequest:
    priority = ApprovalPriority.HIGH if transition.requested_stage in {AutonomyStage.SUPERVISED_AUTOPILOT, AutonomyStage.FROZEN} else ApprovalPriority.MEDIUM
    return ApprovalRequest.objects.create(
        source_type=ApprovalSourceType.OTHER,
        source_object_id=f'autonomy_transition:{transition.id}',
        title=f'Autonomy stage transition for {transition.domain.slug}',
        summary=f'Manual-first approval required to apply stage transition {transition.previous_stage} -> {transition.requested_stage}.',
        priority=priority,
        status=ApprovalRequestStatus.PENDING,
        requested_at=timezone.now(),
        metadata={
            'autonomy_transition_id': transition.id,
            'domain': transition.domain.slug,
            'proposed_stage': transition.requested_stage,
            'trace': {'root_type': 'autonomy_transition', 'root_id': str(transition.id)},
        },
    )


def create_transition_from_recommendation(recommendation: AutonomyStageRecommendation) -> AutonomyStageTransition | None:
    if recommendation.proposed_stage == recommendation.current_stage:
        return None

    existing = AutonomyStageTransition.objects.filter(
        domain=recommendation.domain,
        status__in=[AutonomyTransitionStatus.DRAFT, AutonomyTransitionStatus.PENDING_APPROVAL, AutonomyTransitionStatus.READY_TO_APPLY],
        requested_stage=recommendation.proposed_stage,
    ).first()
    if existing:
        return existing

    transition = AutonomyStageTransition.objects.create(
        domain=recommendation.domain,
        state=recommendation.state,
        recommendation=recommendation,
        status=AutonomyTransitionStatus.DRAFT,
        previous_stage=recommendation.current_stage,
        requested_stage=recommendation.proposed_stage,
        rationale=recommendation.rationale,
        reason_codes=recommendation.reason_codes,
        evidence_refs=recommendation.evidence_refs,
        metadata={'created_from_review': True},
    )

    if _requires_explicit_approval(recommendation):
        transition.approval_request = _build_approval_request(transition)
        transition.status = AutonomyTransitionStatus.PENDING_APPROVAL
    else:
        transition.status = AutonomyTransitionStatus.READY_TO_APPLY
    transition.save(update_fields=['approval_request', 'status', 'updated_at'])
    return transition


def _status_from_stage(stage: str) -> str:
    if stage in {AutonomyStage.FROZEN, AutonomyStage.ROLLBACK_RECOMMENDED}:
        return AutonomyDomainStatus.BLOCKED
    if stage == AutonomyStage.MANUAL:
        return AutonomyDomainStatus.DEGRADED
    if stage == AutonomyStage.SUPERVISED_AUTOPILOT:
        return AutonomyDomainStatus.OBSERVING
    return AutonomyDomainStatus.ACTIVE


@transaction.atomic
def apply_transition(*, transition: AutonomyStageTransition, applied_by: str = 'local-operator') -> AutonomyStageTransition:
    if transition.status == AutonomyTransitionStatus.APPLIED:
        return transition

    if transition.approval_request_id:
        transition.approval_request.refresh_from_db()
        if transition.approval_request.status != ApprovalRequestStatus.APPROVED:
            raise ValueError('Transition requires approval before apply.')

    action_types = list(transition.domain.action_types or [])
    new_tier = TIER_BY_STAGE.get(transition.requested_stage, AutomationTrustTier.MANUAL_ONLY)
    before = list(
        AutomationPolicyRule.objects.filter(action_type__in=action_types).values('id', 'action_type', 'trust_tier')
    )

    AutomationPolicyRule.objects.filter(action_type__in=action_types).update(trust_tier=new_tier)
    after = list(
        AutomationPolicyRule.objects.filter(action_type__in=action_types).values('id', 'action_type', 'trust_tier')
    )

    state = transition.state
    state.current_stage = transition.requested_stage
    state.effective_stage = transition.requested_stage
    state.status = _status_from_stage(transition.requested_stage)
    state.last_changed_at = timezone.now()
    state.rationale = transition.rationale
    state.linked_action_types = action_types
    state.metadata = {
        **(state.metadata or {}),
        'last_transition_id': transition.id,
        'last_transition_at': timezone.now().isoformat(),
    }
    state.save(update_fields=['current_stage', 'effective_stage', 'status', 'last_changed_at', 'rationale', 'linked_action_types', 'metadata', 'updated_at'])

    transition.status = AutonomyTransitionStatus.APPLIED
    transition.applied_stage = transition.requested_stage
    transition.applied_by = applied_by
    transition.applied_at = timezone.now()
    transition.metadata = {
        **(transition.metadata or {}),
        'automation_policy_before': before,
        'automation_policy_after': after,
    }
    transition.save(update_fields=['status', 'applied_stage', 'applied_by', 'applied_at', 'metadata', 'updated_at'])
    return transition


@transaction.atomic
def rollback_transition(*, transition: AutonomyStageTransition, rolled_back_by: str = 'local-operator') -> AutonomyStageTransition:
    if transition.status != AutonomyTransitionStatus.APPLIED:
        raise ValueError('Only applied transitions can be rolled back.')

    action_types = list(transition.domain.action_types or [])
    previous_tier = TIER_BY_STAGE.get(transition.previous_stage, AutomationTrustTier.MANUAL_ONLY)

    AutomationPolicyRule.objects.filter(action_type__in=action_types).update(trust_tier=previous_tier)

    state = transition.state
    state.current_stage = transition.previous_stage
    state.effective_stage = transition.previous_stage
    state.status = _status_from_stage(transition.previous_stage)
    state.last_changed_at = timezone.now()
    state.rationale = f'Rolled back transition #{transition.id}.'
    state.metadata = {
        **(state.metadata or {}),
        'rollback_transition_id': transition.id,
        'rollback_at': timezone.now().isoformat(),
    }
    state.save(update_fields=['current_stage', 'effective_stage', 'status', 'last_changed_at', 'rationale', 'metadata', 'updated_at'])

    transition.status = AutonomyTransitionStatus.ROLLED_BACK
    transition.rolled_back_by = rolled_back_by
    transition.rolled_back_at = timezone.now()
    transition.save(update_fields=['status', 'rolled_back_by', 'rolled_back_at', 'updated_at'])
    return transition


def resolve_transition_readiness(transition: AutonomyStageTransition) -> AutonomyStageTransition:
    if transition.status != AutonomyTransitionStatus.PENDING_APPROVAL or not transition.approval_request_id:
        return transition

    transition.approval_request.refresh_from_db()
    if transition.approval_request.status == ApprovalRequestStatus.APPROVED:
        transition.status = AutonomyTransitionStatus.READY_TO_APPLY
        transition.save(update_fields=['status', 'updated_at'])
    return transition

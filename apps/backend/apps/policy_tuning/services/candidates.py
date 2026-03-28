from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.approval_center.models import ApprovalPriority, ApprovalRequest, ApprovalRequestStatus, ApprovalSourceType
from apps.automation_policy.models import AutomationPolicyProfile, AutomationPolicyRule
from apps.policy_tuning.models import PolicyChangeSet, PolicyTuningCandidate, PolicyTuningCandidateStatus
from apps.trust_calibration.models import TrustCalibrationRecommendation


def _build_evidence_refs(recommendation: TrustCalibrationRecommendation) -> list[dict]:
    refs = [
        {'type': 'trust_calibration_recommendation', 'id': recommendation.id},
        {'type': 'trust_calibration_run', 'id': recommendation.run_id},
        {'type': 'feedback_snapshot', 'id': recommendation.snapshot_id},
    ]
    refs.extend({'type': 'reason_code', 'value': code} for code in recommendation.reason_codes or [])
    return refs


def _active_profile() -> AutomationPolicyProfile:
    profile = AutomationPolicyProfile.objects.filter(is_active=True).first()
    if profile:
        return profile
    fallback = AutomationPolicyProfile.objects.order_by('id').first()
    if fallback:
        return fallback
    return AutomationPolicyProfile.objects.create(slug='policy_tuning_fallback', name='Policy tuning fallback', is_active=True)


def _resolve_rule(*, profile: AutomationPolicyProfile, action_type: str) -> AutomationPolicyRule | None:
    return profile.rules.filter(action_type=action_type, source_context_type='').first()


@transaction.atomic
def create_candidate_from_recommendation(*, recommendation_id: int, status: str | None = None) -> PolicyTuningCandidate:
    recommendation = TrustCalibrationRecommendation.objects.select_related('run', 'snapshot').get(pk=recommendation_id)
    profile = _active_profile()
    rule = _resolve_rule(profile=profile, action_type=recommendation.action_type)

    current_tier = recommendation.current_trust_tier or (rule.trust_tier if rule else '')
    proposed_conditions = (rule.conditions if rule else {}) if recommendation.recommendation_type != 'REVIEW_RULE_CONDITIONS' else recommendation.supporting_metrics

    candidate = PolicyTuningCandidate.objects.create(
        recommendation=recommendation,
        action_type=recommendation.action_type,
        current_profile=profile,
        current_rule=rule,
        current_trust_tier=current_tier,
        proposed_trust_tier=recommendation.recommended_trust_tier,
        proposed_conditions=proposed_conditions,
        rationale=recommendation.rationale,
        confidence=recommendation.confidence,
        evidence_refs=_build_evidence_refs(recommendation),
        status=status or PolicyTuningCandidateStatus.PENDING_APPROVAL,
        metadata={
            'recommendation_type': recommendation.recommendation_type,
            'reason_codes': recommendation.reason_codes,
            'supporting_metrics': recommendation.supporting_metrics,
            'manual_first': True,
            'created_from': 'trust_calibration',
        },
    )

    PolicyChangeSet.objects.create(
        candidate=candidate,
        profile_slug=profile.slug,
        action_type=recommendation.action_type,
        old_trust_tier=current_tier,
        new_trust_tier=recommendation.recommended_trust_tier,
        old_conditions=rule.conditions if rule else {},
        new_conditions=proposed_conditions,
        apply_scope='RULE_ONLY',
        notes='Generated from trust calibration recommendation.',
        metadata={'recommendation_id': recommendation.id},
    )

    approval = ApprovalRequest.objects.create(
        source_type=ApprovalSourceType.OTHER,
        source_object_id=f'policy_tuning_candidate:{candidate.id}',
        title=f'Policy tuning candidate #{candidate.id} · {candidate.action_type}',
        summary='Manual-first policy tuning candidate awaiting operator decision.',
        priority=ApprovalPriority.MEDIUM,
        status=ApprovalRequestStatus.PENDING,
        requested_at=timezone.now(),
        metadata={
            'policy_tuning_candidate_id': candidate.id,
            'trace': {'root_type': 'trust_calibration_run', 'root_id': str(recommendation.run_id)},
            'manual_first': True,
        },
    )
    candidate.approval_request = approval
    candidate.save(update_fields=['approval_request', 'updated_at'])

    return candidate


def list_candidates() -> list[PolicyTuningCandidate]:
    return list(
        PolicyTuningCandidate.objects.select_related('recommendation', 'current_profile', 'current_rule', 'approval_request')
        .prefetch_related('reviews', 'application_logs')
        .order_by('-created_at', '-id')[:200]
    )

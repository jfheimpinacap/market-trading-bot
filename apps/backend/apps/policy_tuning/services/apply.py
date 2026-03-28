from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.automation_policy.models import AutomationPolicyProfile, AutomationPolicyRule
from apps.policy_tuning.models import PolicyTuningApplicationLog, PolicyTuningCandidate, PolicyTuningCandidateStatus


def _active_profile() -> AutomationPolicyProfile:
    profile = AutomationPolicyProfile.objects.filter(is_active=True).first()
    if profile:
        return profile
    fallback = AutomationPolicyProfile.objects.order_by('id').first()
    if fallback:
        return fallback
    return AutomationPolicyProfile.objects.create(slug='policy_tuning_fallback', name='Policy tuning fallback', is_active=True)


@transaction.atomic
def apply_candidate(*, candidate: PolicyTuningCandidate, note: str = '', metadata: dict | None = None) -> PolicyTuningApplicationLog:
    if candidate.status != PolicyTuningCandidateStatus.APPROVED:
        raise ValueError('Only APPROVED candidates can be applied.')

    profile = candidate.current_profile or _active_profile()
    rule = candidate.current_rule or profile.rules.filter(action_type=candidate.action_type, source_context_type='').first()

    if not rule:
        rule = AutomationPolicyRule.objects.create(
            profile=profile,
            action_type=candidate.action_type,
            source_context_type='',
            trust_tier=candidate.current_trust_tier,
            conditions={},
            rationale='Rule materialized from policy tuning candidate apply flow.',
            metadata={'created_by': 'policy_tuning'},
        )

    before_snapshot = {
        'profile_slug': profile.slug,
        'rule_id': rule.id,
        'action_type': rule.action_type,
        'trust_tier': rule.trust_tier,
        'conditions': rule.conditions,
    }

    rule.trust_tier = candidate.proposed_trust_tier or rule.trust_tier
    rule.conditions = candidate.proposed_conditions or rule.conditions
    rule.save(update_fields=['trust_tier', 'conditions', 'updated_at'])

    after_snapshot = {
        'profile_slug': profile.slug,
        'rule_id': rule.id,
        'action_type': rule.action_type,
        'trust_tier': rule.trust_tier,
        'conditions': rule.conditions,
    }

    candidate.status = PolicyTuningCandidateStatus.APPLIED
    candidate.current_profile = profile
    candidate.current_rule = rule
    candidate.metadata = {
        **(candidate.metadata or {}),
        'last_applied_at': timezone.now().isoformat(),
        'last_apply_note': note,
    }
    candidate.save(update_fields=['status', 'current_profile', 'current_rule', 'metadata', 'updated_at'])

    return PolicyTuningApplicationLog.objects.create(
        candidate=candidate,
        applied_to_profile=profile,
        applied_to_rule=rule,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        applied_at=timezone.now(),
        result_summary='Policy rule updated manually from approved tuning candidate.',
        metadata={
            **(metadata or {}),
            'manual_first': True,
            'paper_only': True,
            'note': note,
        },
    )

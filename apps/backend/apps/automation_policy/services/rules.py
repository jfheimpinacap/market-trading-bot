from django.db import transaction

from apps.automation_policy.models import AutomationPolicyProfile, AutomationPolicyRule, AutomationTrustTier

BASE_RULES = [
    ('run_incident_detection', '', AutomationTrustTier.SAFE_AUTOMATION, 'Detection is read/evaluation oriented and safe in paper mode.'),
    ('run_certification_review', '', AutomationTrustTier.SAFE_AUTOMATION, 'Certification review is non-execution governance.'),
    ('run_profile_governance', '', AutomationTrustTier.SAFE_AUTOMATION, 'Profile governance is constrained and auditable.'),
    ('run_portfolio_governance', '', AutomationTrustTier.SAFE_AUTOMATION, 'Portfolio governance produces guidance under guardrails.'),
    ('run_venue_reconciliation', '', AutomationTrustTier.SAFE_AUTOMATION, 'Reconciliation is a safe parity check action.'),
    ('open_trace', '', AutomationTrustTier.SAFE_AUTOMATION, 'Trace recommendation/query is non-invasive.'),
    ('pause_mission_control', '', AutomationTrustTier.APPROVAL_REQUIRED, 'Mission pause impacts orchestration and needs supervision.'),
    ('pause_rollout', '', AutomationTrustTier.APPROVAL_REQUIRED, 'Rollout pause has system-wide impact and requires approval.'),
    ('rollback_rollout', '', AutomationTrustTier.APPROVAL_REQUIRED, 'Rollback must stay operator-supervised.'),
    ('resolve_incident', '', AutomationTrustTier.MANUAL_ONLY, 'Incident resolution requires explicit human judgment.'),
    ('live_execution', '', AutomationTrustTier.AUTO_BLOCKED, 'Live execution domain is hard-blocked in this phase.'),
    ('broker_order_submit', '', AutomationTrustTier.AUTO_BLOCKED, 'Broker/live execution pathways are blocked for autopilot.'),
]

PROFILE_OVERRIDES = {
    'conservative_manual_first': {
        'run_incident_detection': AutomationTrustTier.APPROVAL_REQUIRED,
        'run_certification_review': AutomationTrustTier.APPROVAL_REQUIRED,
        'run_profile_governance': AutomationTrustTier.APPROVAL_REQUIRED,
        'run_portfolio_governance': AutomationTrustTier.APPROVAL_REQUIRED,
        'run_venue_reconciliation': AutomationTrustTier.APPROVAL_REQUIRED,
        'open_trace': AutomationTrustTier.APPROVAL_REQUIRED,
    },
    'supervised_autopilot': {
        'pause_mission_control': AutomationTrustTier.SAFE_AUTOMATION,
        'pause_rollout': AutomationTrustTier.SAFE_AUTOMATION,
    },
}


def _tier_for_profile(profile_slug: str, action_type: str, default_tier: str) -> str:
    return PROFILE_OVERRIDES.get(profile_slug, {}).get(action_type, default_tier)


@transaction.atomic
def ensure_default_rules() -> None:
    profiles = AutomationPolicyProfile.objects.all()
    for profile in profiles:
        for action_type, source_context_type, default_tier, rationale in BASE_RULES:
            tier = _tier_for_profile(profile.slug, action_type, default_tier)
            AutomationPolicyRule.objects.update_or_create(
                profile=profile,
                action_type=action_type,
                source_context_type=source_context_type,
                defaults={
                    'trust_tier': tier,
                    'rationale': rationale,
                    'conditions': {'paper_only': True},
                    'metadata': {'bootstrap': True},
                },
            )


def list_rules(*, profile: AutomationPolicyProfile) -> list[AutomationPolicyRule]:
    ensure_default_rules()
    return list(profile.rules.order_by('action_type', 'source_context_type', 'id'))


def resolve_rule(*, profile: AutomationPolicyProfile, action_type: str, source_context_type: str = '') -> AutomationPolicyRule | None:
    ensure_default_rules()
    source_context_type = source_context_type or ''
    specific = profile.rules.filter(action_type=action_type, source_context_type=source_context_type).first()
    if specific:
        return specific
    return profile.rules.filter(action_type=action_type, source_context_type='').first()

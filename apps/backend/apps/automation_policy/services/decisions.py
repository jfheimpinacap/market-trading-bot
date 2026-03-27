from dataclasses import dataclass

from apps.automation_policy.models import AutomationDecision, AutomationDecisionOutcome, AutomationTrustTier
from apps.automation_policy.services.guardrails import apply_guardrails
from apps.automation_policy.services.profiles import get_active_profile
from apps.automation_policy.services.rules import resolve_rule


@dataclass
class DecisionResult:
    decision: AutomationDecision
    can_auto_execute: bool
    approval_required: bool
    blocked: bool


def _outcome_for_tier(tier: str) -> str:
    if tier == AutomationTrustTier.AUTO_BLOCKED:
        return AutomationDecisionOutcome.BLOCKED
    if tier == AutomationTrustTier.MANUAL_ONLY:
        return AutomationDecisionOutcome.MANUAL_ONLY
    if tier == AutomationTrustTier.APPROVAL_REQUIRED:
        return AutomationDecisionOutcome.APPROVAL_REQUIRED
    return AutomationDecisionOutcome.ALLOWED


def evaluate_action(*, action_type: str, source_context_type: str = '', runbook_instance_id: int | None = None, runbook_step_id: int | None = None, metadata: dict | None = None) -> DecisionResult:
    profile = get_active_profile()
    rule = resolve_rule(profile=profile, action_type=action_type, source_context_type=source_context_type)

    trust_tier = rule.trust_tier if rule else AutomationTrustTier.MANUAL_ONLY
    rationale = rule.rationale if rule else 'No explicit rule found; defaulting to manual-only policy.'

    effective_tier, guardrail_reasons, guardrail_context = apply_guardrails(
        proposed_tier=trust_tier,
        action_type=action_type,
        recommendation_mode=bool(profile.recommendation_mode),
    )

    outcome = _outcome_for_tier(effective_tier)
    if profile.recommendation_mode and outcome == AutomationDecisionOutcome.ALLOWED:
        outcome = AutomationDecisionOutcome.APPROVAL_REQUIRED

    decision = AutomationDecision.objects.create(
        profile=profile,
        rule=rule,
        action_type=action_type,
        source_context_type=source_context_type or '',
        runbook_instance_id=runbook_instance_id,
        runbook_step_id=runbook_step_id,
        trust_tier=trust_tier,
        effective_trust_tier=effective_tier,
        outcome=outcome,
        reason_codes=guardrail_reasons,
        rationale=rationale,
        metadata={
            'request_metadata': metadata or {},
            'guardrail_context': guardrail_context,
            'recommendation_mode': bool(profile.recommendation_mode),
        },
    )

    return DecisionResult(
        decision=decision,
        can_auto_execute=outcome == AutomationDecisionOutcome.ALLOWED and not profile.recommendation_mode,
        approval_required=outcome == AutomationDecisionOutcome.APPROVAL_REQUIRED,
        blocked=outcome == AutomationDecisionOutcome.BLOCKED,
    )

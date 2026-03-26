from decimal import Decimal

from apps.signals.models import OpportunityStatus
from apps.signals.services.profiles import SignalProfileConfig


def build_proposal_gate_decision(*, opportunity, profile: SignalProfileConfig):
    constraints = opportunity.runtime_constraints or {}
    safety_status = str(constraints.get('safety_status') or '').upper()
    runtime_status = str(constraints.get('runtime_status') or '').upper()
    runtime_allow_proposals = bool(constraints.get('runtime_allow_proposals', True))

    blocked_reason = ''
    should_generate = False
    priority = 0
    reason = 'Signal quality is not high enough for proposal generation yet.'

    if opportunity.opportunity_status == OpportunityStatus.BLOCKED:
        blocked_reason = opportunity.rationale[:240]
    elif not runtime_allow_proposals:
        blocked_reason = 'Runtime mode currently disallows proposal generation.'
    elif runtime_status in {'PAUSED', 'STOPPED', 'DEGRADED'}:
        blocked_reason = f'Runtime governor status is {runtime_status}.'
    elif safety_status in {'PAUSED', 'HARD_STOP', 'KILL_SWITCH', 'COOLDOWN'}:
        blocked_reason = f'Safety guard status is {safety_status}.'
    elif opportunity.opportunity_status == OpportunityStatus.PROPOSAL_READY:
        should_generate = True
        priority = 100 if opportunity.opportunity_score >= Decimal('80.00') else 85 if opportunity.opportunity_score >= Decimal('72.00') else 70
        reason = 'Composite signal is proposal-ready under current profile thresholds.'
    elif opportunity.opportunity_status == OpportunityStatus.CANDIDATE:
        priority = 40
        reason = 'Candidate signal is promising but still below proposal-ready quality gate.'
    elif opportunity.opportunity_status == OpportunityStatus.WATCH:
        priority = 10
        reason = 'Watch-only signal should stay monitored until edge/confidence improves.'

    if blocked_reason:
        priority = 0
        reason = 'Proposal generation blocked by risk/runtime/safety constraints.'

    return {
        'should_generate_proposal': should_generate,
        'proposal_priority': priority,
        'proposal_reason': reason,
        'blocked_reason': blocked_reason,
        'metadata': {
            'profile': profile.slug,
            'opportunity_status': opportunity.opportunity_status,
            'opportunity_score': str(opportunity.opportunity_score),
        },
    }

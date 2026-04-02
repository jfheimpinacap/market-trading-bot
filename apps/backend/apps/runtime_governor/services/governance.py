from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.readiness_lab.models import ReadinessAssessmentRun, ReadinessStatus
from apps.runtime_governor.models import RuntimeMode, RuntimeSetBy, RuntimeStateStatus
from apps.runtime_governor.services.capabilities import get_effective_capabilities
from apps.runtime_governor.services.operating_mode.mode_switch import build_downstream_influence, get_active_global_operating_mode
from apps.runtime_governor.services.state import get_mode_profile, get_runtime_state, list_mode_profiles
from apps.runtime_governor.services.transitions import log_transition
from apps.safety_guard.services.evaluation import get_safety_status

MODE_ORDER = {
    RuntimeMode.OBSERVE_ONLY: 0,
    RuntimeMode.PAPER_ASSIST: 1,
    RuntimeMode.PAPER_SEMI_AUTO: 2,
    RuntimeMode.PAPER_AUTO: 3,
}


@dataclass
class GovernanceDecision:
    allowed: bool
    target_mode: str
    status: str
    reasons: list[str]


def _latest_readiness_status() -> str | None:
    run = ReadinessAssessmentRun.objects.order_by('-created_at', '-id').first()
    return run.status if run else None


def evaluate_mode_constraints(*, requested_mode: str) -> GovernanceDecision:
    reasons: list[str] = []
    readiness = _latest_readiness_status()
    safety = get_safety_status()

    if readiness == ReadinessStatus.NOT_READY and requested_mode in {RuntimeMode.PAPER_SEMI_AUTO, RuntimeMode.PAPER_AUTO}:
        reasons.append('Readiness is NOT_READY, so semi-auto and auto modes are blocked.')
    if readiness == ReadinessStatus.CAUTION and requested_mode == RuntimeMode.PAPER_AUTO:
        reasons.append('Readiness is CAUTION, so PAPER_AUTO is blocked.')

    if safety['kill_switch_enabled']:
        if requested_mode != RuntimeMode.OBSERVE_ONLY:
            reasons.append('Kill switch enabled: only OBSERVE_ONLY is permitted.')
        return GovernanceDecision(
            allowed=requested_mode == RuntimeMode.OBSERVE_ONLY,
            target_mode=RuntimeMode.OBSERVE_ONLY,
            status=RuntimeStateStatus.STOPPED,
            reasons=reasons or ['Kill switch enabled.'],
        )

    if safety['hard_stop_active'] and requested_mode != RuntimeMode.OBSERVE_ONLY:
        reasons.append('Hard stop active: runtime must remain in OBSERVE_ONLY.')

    if safety['status'] in {'COOLDOWN', 'PAUSED'} and requested_mode in {RuntimeMode.PAPER_SEMI_AUTO, RuntimeMode.PAPER_AUTO}:
        reasons.append(f"Safety status {safety['status']} blocks semi-auto and auto execution modes.")

    allowed = len(reasons) == 0
    status = RuntimeStateStatus.ACTIVE if allowed else RuntimeStateStatus.DEGRADED
    return GovernanceDecision(allowed=allowed, target_mode=requested_mode, status=status, reasons=reasons)


def set_runtime_mode(*, requested_mode: str, set_by: str = RuntimeSetBy.OPERATOR, rationale: str = '', metadata: dict | None = None) -> dict:
    state = get_runtime_state()
    before = type(state).objects.get(pk=state.pk)
    decision = evaluate_mode_constraints(requested_mode=requested_mode)

    if not decision.allowed:
        return {
            'changed': False,
            'state': state,
            'decision': decision,
        }

    if state.current_mode == requested_mode and state.status == decision.status:
        return {'changed': False, 'state': state, 'decision': decision}

    state.current_mode = requested_mode
    state.desired_mode = None
    state.status = decision.status
    state.set_by = set_by
    state.rationale = rationale or f'Mode changed to {requested_mode}.'
    state.metadata = {**(metadata or {}), 'decision_reasons': decision.reasons}
    state.effective_at = timezone.now()
    state.save(update_fields=['current_mode', 'desired_mode', 'status', 'set_by', 'rationale', 'metadata', 'effective_at', 'updated_at'])
    log_transition(state_before=before, state_after=state, trigger_source=set_by, reason=state.rationale, metadata=state.metadata)
    return {'changed': True, 'state': state, 'decision': decision}


def reconcile_runtime_state(*, reason: str = 'Runtime reconciliation with readiness/safety constraints.') -> dict:
    state = get_runtime_state()
    decision = evaluate_mode_constraints(requested_mode=state.current_mode)
    if decision.allowed:
        return {'changed': False, 'state': state, 'decision': decision}

    fallback_mode = RuntimeMode.OBSERVE_ONLY
    if MODE_ORDER.get(state.current_mode, 0) > MODE_ORDER[RuntimeMode.OBSERVE_ONLY]:
        fallback_mode = RuntimeMode.PAPER_ASSIST if decision.target_mode != RuntimeMode.OBSERVE_ONLY else RuntimeMode.OBSERVE_ONLY

    fallback_decision = evaluate_mode_constraints(requested_mode=fallback_mode)
    if not fallback_decision.allowed:
        fallback_mode = RuntimeMode.OBSERVE_ONLY
        fallback_decision = evaluate_mode_constraints(requested_mode=fallback_mode)

    return set_runtime_mode(
        requested_mode=fallback_mode,
        set_by=RuntimeSetBy.SAFETY if 'Safety' in ' '.join(decision.reasons) or 'Kill switch' in ' '.join(decision.reasons) else RuntimeSetBy.READINESS,
        rationale=reason,
        metadata={'degraded_from': state.current_mode, 'blocking_reasons': decision.reasons},
    )


def get_runtime_status() -> dict:
    reconcile_runtime_state(reason='Automatic reconciliation while reading runtime status.')
    state = get_runtime_state()
    profile = get_mode_profile(state.current_mode)
    readiness = _latest_readiness_status()
    safety = get_safety_status()
    decision = evaluate_mode_constraints(requested_mode=state.current_mode)
    global_mode = get_active_global_operating_mode()
    return {
        'state': state,
        'profile': profile,
        'readiness_status': readiness,
        'safety_status': safety,
        'constraints': {'allowed': decision.allowed, 'reasons': decision.reasons},
        'global_operating_mode': global_mode,
        'global_mode_influence': build_downstream_influence(mode=global_mode),
        'global_mode_enforcement': (state.metadata or {}).get('global_mode_enforcement', {}),
        'global_mode_enforcement_run_id': (state.metadata or {}).get('global_mode_enforcement_run_id'),
    }


def list_modes_with_constraints() -> list[dict]:
    readiness = _latest_readiness_status()
    safety = get_safety_status()
    rows: list[dict] = []
    for profile in list_mode_profiles():
        decision = evaluate_mode_constraints(requested_mode=profile.mode)
        rows.append({
            'mode': profile.mode,
            'label': profile.label,
            'description': profile.description,
            'is_allowed_now': decision.allowed,
            'blocked_reasons': decision.reasons,
            'readiness_status': readiness,
            'safety_status': safety['status'],
        })
    return rows


def get_capabilities_for_current_mode() -> dict:
    state = get_runtime_state()
    profile = get_mode_profile(state.current_mode)
    return get_effective_capabilities(profile)

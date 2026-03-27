from __future__ import annotations

from apps.profile_manager.models import ProfileDecisionMode, RegimeClassification
from apps.profile_manager.services.profiles import resolve_profile


def build_profile_decision(*, regime: str, state: dict, requested_mode: str | None = None, reason_codes: list[str] | None = None, constraints: list[str] | None = None) -> dict:
    reason_codes = reason_codes or []
    constraints = constraints or []

    if regime in {RegimeClassification.BLOCKED, RegimeClassification.DEFENSIVE, RegimeClassification.DRAWDOWN_MODE, RegimeClassification.CONCENTRATED, RegimeClassification.STRESSED}:
        operating_mode = 'conservative'
    else:
        operating_mode = 'balanced'

    decision_mode = requested_mode or ProfileDecisionMode.RECOMMEND_ONLY
    if decision_mode == ProfileDecisionMode.APPLY_FORCED and regime not in {RegimeClassification.BLOCKED, RegimeClassification.DEFENSIVE}:
        decision_mode = ProfileDecisionMode.APPLY_SAFE

    if regime in {RegimeClassification.BLOCKED, RegimeClassification.DEFENSIVE, RegimeClassification.DRAWDOWN_MODE} and requested_mode is None:
        decision_mode = ProfileDecisionMode.APPLY_SAFE

    if state.get('runtime_mode') == 'OBSERVE_ONLY' and operating_mode != 'conservative':
        operating_mode = 'conservative'
        constraints.append('RUNTIME_OBSERVE_ONLY')

    if state.get('readiness_status') == 'NOT_READY':
        operating_mode = 'conservative'
        constraints.append('READINESS_BLOCK')

    targets = {
        'target_research_profile': resolve_profile('research_agent', operating_mode),
        'target_signal_profile': resolve_profile('signals', operating_mode),
        'target_opportunity_supervisor_profile': resolve_profile('opportunity_supervisor', operating_mode),
        'target_mission_control_profile': resolve_profile('mission_control', operating_mode),
        'target_portfolio_governor_profile': resolve_profile('portfolio_governor', operating_mode),
        'target_prediction_profile': '',
    }

    rationale = (
        f"Regime={regime}. Runtime={state.get('runtime_mode')}, readiness={state.get('readiness_status')}, "
        f"safety={state.get('safety_status')}, throttle={state.get('throttle_state')}. "
        f"Selected {operating_mode} profile pack with mode {decision_mode}."
    )

    return {
        **targets,
        'decision_mode': decision_mode,
        'rationale': rationale,
        'reason_codes': sorted(set(reason_codes)),
        'blocking_constraints': sorted(set(constraints)),
        'metadata': {
            'operating_mode': operating_mode,
            'paper_demo_only': True,
            'real_execution_enabled': False,
            'state_snapshot': state,
        },
    }

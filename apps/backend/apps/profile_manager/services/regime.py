from __future__ import annotations

from apps.profile_manager.models import RegimeClassification


def classify_regime(state: dict) -> tuple[str, list[str], list[str]]:
    reason_codes: list[str] = []
    constraints: list[str] = []

    if state.get('safety_kill_switch') or state.get('safety_hard_stop'):
        reason_codes.extend(['safety_block'])
        constraints.extend(['SAFETY_BLOCK'])
        return RegimeClassification.BLOCKED, reason_codes, constraints

    if state.get('readiness_status') == 'NOT_READY':
        reason_codes.append('readiness_not_ready')
        constraints.append('READINESS_BLOCK')
        return RegimeClassification.BLOCKED, reason_codes, constraints

    if state.get('runtime_mode') == 'OBSERVE_ONLY':
        reason_codes.append('runtime_observe_only')
        constraints.append('RUNTIME_OBSERVE_ONLY')

    if state.get('throttle_state') in {'FORCE_REDUCE', 'BLOCK_NEW_ENTRIES'}:
        reason_codes.append('portfolio_throttle_block')
        constraints.append('PORTFOLIO_BLOCK')
        return RegimeClassification.DEFENSIVE, reason_codes, constraints

    if state.get('drawdown_pct', 0) >= 0.10:
        reason_codes.append('drawdown_high')
        return RegimeClassification.DRAWDOWN_MODE, reason_codes, constraints

    if state.get('market_concentration', 0) >= 0.45 or state.get('provider_concentration', 0) >= 0.55:
        reason_codes.append('concentration_high')
        return RegimeClassification.CONCENTRATED, reason_codes, constraints

    if state.get('throttle_state') == 'THROTTLED' or state.get('queue_pressure', 0) >= 8:
        reason_codes.append('system_stressed')
        return RegimeClassification.STRESSED, reason_codes, constraints

    if state.get('throttle_state') == 'CAUTION' or state.get('drawdown_pct', 0) >= 0.06:
        reason_codes.append('caution_signal')
        return RegimeClassification.CAUTION, reason_codes, constraints

    reason_codes.append('stable')
    return RegimeClassification.NORMAL, reason_codes, constraints

from __future__ import annotations

from apps.runtime_governor.services import get_runtime_state
from apps.safety_guard.services import get_safety_status


def detect_regime_signals(*, snapshot: dict, profile: dict, queue_pressure: int, close_reduce_events: int) -> list[str]:
    runtime = get_runtime_state()
    safety = get_safety_status()
    signals: list[str] = ['normal']

    if snapshot['concentration_market_ratio'] >= profile['max_market_concentration_ratio'] or snapshot['concentration_provider_ratio'] >= profile['max_provider_concentration_ratio']:
        signals.append('concentrated')
    if float(snapshot['recent_drawdown_pct']) >= float(profile['drawdown_caution_pct']):
        signals.append('drawdown_caution')
    if float(snapshot['cash_reserve_ratio']) <= float(profile['cash_reserve_caution_ratio']):
        signals.append('capital_tight')
    if queue_pressure >= profile['queue_pressure_caution']:
        signals.append('queue_pressure')
    if close_reduce_events >= profile['close_reduce_events_caution']:
        signals.append('defensive_lifecycle_activity')
    if safety.get('kill_switch_enabled') or safety.get('hard_stop_active'):
        signals.append('safety_pressure')
    if runtime.current_mode in {'OBSERVE_ONLY', 'PAPER_ASSIST'}:
        signals.append('runtime_conservative')

    return list(dict.fromkeys(signals))

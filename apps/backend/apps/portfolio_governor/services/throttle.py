from __future__ import annotations

from decimal import Decimal

from apps.portfolio_governor.models import PortfolioThrottleState


def build_throttle_decision_payload(*, snapshot: dict, profile: dict, regime_signals: list[str], queue_pressure: int, close_reduce_events: int, runtime_mode: str, safety_status: dict) -> dict:
    reason_codes: list[str] = []
    state = PortfolioThrottleState.NORMAL
    max_new = profile['default_max_new_positions']
    size_multiplier = Decimal('1.0')

    drawdown = float(snapshot['recent_drawdown_pct'])
    market_concentration = float(snapshot['concentration_market_ratio'])
    provider_concentration = float(snapshot['concentration_provider_ratio'])
    reserve_ratio = float(snapshot['cash_reserve_ratio'])
    open_positions = int(snapshot['open_positions'])

    if safety_status.get('kill_switch_enabled') or safety_status.get('hard_stop_active'):
        state = PortfolioThrottleState.BLOCK_NEW_ENTRIES
        reason_codes.append('SAFETY_GUARD_ACTIVE')

    if drawdown >= float(profile['drawdown_block_pct']) or reserve_ratio <= float(profile['cash_reserve_block_ratio']):
        state = PortfolioThrottleState.BLOCK_NEW_ENTRIES
        reason_codes.append('PORTFOLIO_DRAWDOWN_OR_CAPITAL_BLOCK')

    if state != PortfolioThrottleState.BLOCK_NEW_ENTRIES:
        if (
            drawdown >= float(profile['drawdown_throttle_pct'])
            or market_concentration >= float(profile['max_market_concentration_ratio'])
            or provider_concentration >= float(profile['max_provider_concentration_ratio'])
            or queue_pressure >= int(profile['queue_pressure_throttle'])
            or close_reduce_events >= int(profile['close_reduce_events_throttle'])
            or reserve_ratio <= float(profile['cash_reserve_throttle_ratio'])
        ):
            state = PortfolioThrottleState.THROTTLED
            max_new = 1
            size_multiplier = Decimal('0.50')
            reason_codes.append('EXPOSURE_THROTTLED')
        elif (
            drawdown >= float(profile['drawdown_caution_pct'])
            or reserve_ratio <= float(profile['cash_reserve_caution_ratio'])
            or open_positions >= int(profile['max_open_positions'])
            or 'concentrated' in regime_signals
        ):
            state = PortfolioThrottleState.CAUTION
            max_new = min(max_new, 2)
            size_multiplier = Decimal('0.75')
            reason_codes.append('EXPOSURE_CAUTION')

    if runtime_mode == 'OBSERVE_ONLY':
        max_new = 0
        size_multiplier = Decimal('0')
        state = PortfolioThrottleState.BLOCK_NEW_ENTRIES
        reason_codes.append('RUNTIME_OBSERVE_ONLY')

    rationale = (
        f"State={state}; drawdown={drawdown:.3f}; market_concentration={market_concentration:.3f}; "
        f"provider_concentration={provider_concentration:.3f}; reserve_ratio={reserve_ratio:.3f}."
    )

    return {
        'state': state,
        'rationale': rationale,
        'reason_codes': list(dict.fromkeys(reason_codes)),
        'recommended_max_new_positions': max_new,
        'recommended_max_size_multiplier': size_multiplier,
        'regime_signals': regime_signals,
        'metadata': {
            'queue_pressure': queue_pressure,
            'recent_close_reduce_events': close_reduce_events,
            'runtime_mode': runtime_mode,
            'safety_status': safety_status.get('status'),
            'paper_demo_only': True,
            'real_execution_enabled': False,
        },
    }

from __future__ import annotations

from decimal import Decimal


def _to_decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal('0')


def build_execution_comparison(*, naive_metrics: dict, aware_metrics: dict) -> dict:
    naive_pnl = _to_decimal(naive_metrics.get('total_pnl'))
    aware_pnl = _to_decimal(aware_metrics.get('execution_adjusted_pnl') or aware_metrics.get('total_pnl'))
    execution_drag = (naive_pnl - aware_pnl).quantize(Decimal('0.01'))
    return {
        'naive_mode': naive_metrics.get('execution_mode', 'naive'),
        'aware_mode': aware_metrics.get('execution_mode', 'execution_aware'),
        'naive_total_pnl': str(naive_pnl),
        'aware_total_pnl': str(aware_pnl),
        'execution_drag': str(execution_drag),
        'fill_rate_delta': str(_to_decimal(aware_metrics.get('fill_rate')) - _to_decimal(naive_metrics.get('fill_rate'))),
        'no_fill_rate_delta': str(_to_decimal(aware_metrics.get('no_fill_rate')) - _to_decimal(naive_metrics.get('no_fill_rate'))),
    }

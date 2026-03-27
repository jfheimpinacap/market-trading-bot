from __future__ import annotations

from decimal import Decimal


def _to_decimal(value: object, default: str = '0') -> Decimal:
    if value is None:
        return Decimal(default)
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def normalize_replay_metrics(run) -> dict:
    details = run.details or {}
    impact = details.get('execution_impact_summary', {})

    proposals = int(run.proposals_generated or 0)
    approvals = int(run.approvals_required or 0)
    blocked = int(run.blocked_count or 0)
    queued = approvals
    fills = int(run.trades_executed or 0)

    review_pressure = (approvals + blocked) / proposals if proposals else 0
    drawdown_proxy = max(float(-_to_decimal(run.total_pnl) / Decimal('10000')), 0)

    return {
        'markets_evaluated': int(run.markets_considered or 0),
        'opportunity_count': int(run.markets_considered or 0),
        'proposal_ready_count': proposals,
        'queue_count': queued,
        'block_count': blocked,
        'fill_count': fills,
        'fill_rate': float(impact.get('fill_rate', 0) or 0),
        'partial_fill_rate': float(impact.get('partial_fill_rate', 0) or 0),
        'no_fill_rate': float(impact.get('no_fill_rate', 0) or 0),
        'execution_adjusted_pnl': str(impact.get('execution_adjusted_pnl', run.total_pnl)),
        'execution_drag': str(impact.get('execution_drag', '0')),
        'drawdown_proxy': drawdown_proxy,
        'risk_review_pressure': review_pressure,
    }


def compare_metrics(*, champion: dict, challenger: dict) -> dict:
    divergence_numerator = (
        abs(champion['proposal_ready_count'] - challenger['proposal_ready_count'])
        + abs(champion['queue_count'] - challenger['queue_count'])
        + abs(champion['block_count'] - challenger['block_count'])
    )
    divergence_denominator = max(
        champion['proposal_ready_count'] + champion['queue_count'] + champion['block_count'],
        1,
    )

    deltas = {
        'opportunity_delta': challenger['opportunity_count'] - champion['opportunity_count'],
        'proposal_delta': challenger['proposal_ready_count'] - champion['proposal_ready_count'],
        'queue_delta': challenger['queue_count'] - champion['queue_count'],
        'block_delta': challenger['block_count'] - champion['block_count'],
        'fill_rate_delta': challenger['fill_rate'] - champion['fill_rate'],
        'partial_fill_rate_delta': challenger['partial_fill_rate'] - champion['partial_fill_rate'],
        'no_fill_rate_delta': challenger['no_fill_rate'] - champion['no_fill_rate'],
        'execution_adjusted_pnl_delta': str(
            _to_decimal(challenger['execution_adjusted_pnl']) - _to_decimal(champion['execution_adjusted_pnl'])
        ),
        'execution_drag_delta': str(_to_decimal(challenger['execution_drag']) - _to_decimal(champion['execution_drag'])),
        'drawdown_proxy_delta': challenger['drawdown_proxy'] - champion['drawdown_proxy'],
        'risk_review_pressure_delta': challenger['risk_review_pressure'] - champion['risk_review_pressure'],
    }

    return {
        'champion_metrics': champion,
        'challenger_metrics': challenger,
        'deltas': deltas,
        'decision_divergence_rate': divergence_numerator / divergence_denominator,
    }

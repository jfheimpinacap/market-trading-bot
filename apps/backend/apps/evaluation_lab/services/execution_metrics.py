from __future__ import annotations

from decimal import Decimal

from apps.execution_simulator.models import PaperExecutionAttempt, PaperExecutionAttemptStatus


def build_execution_metrics(*, started_at, finished_at) -> dict:
    attempts = PaperExecutionAttempt.objects.filter(created_at__gte=started_at, created_at__lte=finished_at)
    total_attempts = attempts.count()
    if total_attempts == 0:
        return {
            'total_attempts': 0,
            'fill_rate': 0.0,
            'partial_fill_rate': 0.0,
            'no_fill_rate': 0.0,
            'cancelled_ratio': 0.0,
            'expired_ratio': 0.0,
            'avg_slippage_bps': 0.0,
            'avg_slippage_pct': 0.0,
            'execution_adjusted_pnl': '0',
            'execution_drag': '0',
            'execution_realism_score': 0.0,
            'execution_quality_bucket': 'NO_DATA',
        }

    success_count = attempts.filter(attempt_status=PaperExecutionAttemptStatus.SUCCESS).count()
    partial_count = attempts.filter(attempt_status=PaperExecutionAttemptStatus.PARTIAL).count()
    no_fill_count = attempts.filter(attempt_status=PaperExecutionAttemptStatus.NO_FILL).count()
    cancelled_count = attempts.filter(attempt_status=PaperExecutionAttemptStatus.CANCELLED).count()
    expired_count = attempts.filter(attempt_status=PaperExecutionAttemptStatus.EXPIRED).count()

    slippage_values = [attempt.slippage_bps for attempt in attempts if attempt.slippage_bps is not None]
    avg_slippage_bps = float(sum(slippage_values, Decimal('0')) / Decimal(len(slippage_values))) if slippage_values else 0.0
    avg_slippage_pct = avg_slippage_bps / 10000

    fill_rate = success_count / total_attempts
    partial_fill_rate = partial_count / total_attempts
    no_fill_rate = no_fill_count / total_attempts
    cancel_ratio = cancelled_count / total_attempts
    expired_ratio = expired_count / total_attempts

    realism_score = max(
        0.0,
        min(
            1.0,
            (fill_rate * 0.55)
            + ((1 - no_fill_rate) * 0.2)
            + ((1 - min(avg_slippage_bps / 150, 1.0)) * 0.15)
            + ((1 - cancel_ratio - expired_ratio) * 0.1),
        ),
    )

    if realism_score >= 0.75:
        quality_bucket = 'HIGH_FILL_RATE'
    elif no_fill_rate >= 0.35:
        quality_bucket = 'NO_FILL_RISK'
    elif avg_slippage_bps >= 60:
        quality_bucket = 'HIGH_SLIPPAGE'
    else:
        quality_bucket = 'BALANCED_EXECUTION'

    fill_ratio = min(1.0, fill_rate + (partial_fill_rate * 0.5))

    return {
        'total_attempts': total_attempts,
        'fill_rate': round(fill_rate, 4),
        'partial_fill_rate': round(partial_fill_rate, 4),
        'no_fill_rate': round(no_fill_rate, 4),
        'cancelled_ratio': round(cancel_ratio, 4),
        'expired_ratio': round(expired_ratio, 4),
        'avg_slippage_bps': round(avg_slippage_bps, 2),
        'avg_slippage_pct': round(avg_slippage_pct, 6),
        'fill_ratio': round(fill_ratio, 4),
        'execution_realism_score': round(realism_score, 4),
        'execution_quality_bucket': quality_bucket,
    }


def merge_execution_pnl(*, total_pnl, execution_metrics: dict) -> dict:
    pnl = Decimal(str(total_pnl or 0))
    fill_ratio = Decimal(str(execution_metrics.get('fill_ratio', 1.0)))
    execution_adjusted_pnl = (pnl * fill_ratio).quantize(Decimal('0.01'))
    execution_drag = (pnl - execution_adjusted_pnl).quantize(Decimal('0.01'))
    return {
        **execution_metrics,
        'execution_adjusted_pnl': str(execution_adjusted_pnl),
        'execution_drag': str(execution_drag),
    }

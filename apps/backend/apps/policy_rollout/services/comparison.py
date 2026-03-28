from __future__ import annotations

from decimal import Decimal


DELTA_KEYS = [
    'approval_rate',
    'rejection_rate',
    'expiry_rate',
    'escalation_rate',
    'auto_execution_success_rate',
    'approval_friction_score',
    'operator_override_rate',
    'manual_intervention_rate',
    'auto_action_followed_by_incident_rate',
]


def _to_decimal(value: object) -> Decimal:
    return Decimal(str(value or '0'))


def build_metric_deltas(*, baseline_metrics: dict, post_metrics: dict) -> dict:
    deltas = {}
    for key in DELTA_KEYS:
        before = _to_decimal(baseline_metrics.get(key))
        after = _to_decimal(post_metrics.get(key))
        deltas[key] = str((after - before).quantize(Decimal('0.0001')))
    deltas['sample_size_delta'] = int(post_metrics.get('sample_size') or 0) - int(baseline_metrics.get('sample_size') or 0)
    return deltas

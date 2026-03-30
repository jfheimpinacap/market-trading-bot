from __future__ import annotations

from apps.promotion_committee.models import ManualRolloutPlan


def collect_post_rollout_flags(*, plan: ManualRolloutPlan) -> dict[str, list[str] | dict[str, int]]:
    """Collect bounded review flags from plan metadata and monitoring intent."""

    monitoring_intent = plan.monitoring_intent or {}
    plan_metadata = plan.metadata or {}

    drift_flags = list(monitoring_intent.get('drift_flags') or [])
    risk_flags = list(monitoring_intent.get('risk_flags') or [])
    calibration_flags = list(monitoring_intent.get('calibration_flags') or [])

    if plan.target_component == 'risk' and 'risk_runtime_review' not in risk_flags:
        risk_flags.append('risk_runtime_review')
    if plan.target_component == 'calibration' and 'trust_calibration_review' not in calibration_flags:
        calibration_flags.append('trust_calibration_review')
    if plan.target_component == 'prediction' and 'prediction_quality_review' not in drift_flags:
        drift_flags.append('prediction_quality_review')

    linked_context: dict[str, int] = {}
    for key in ('evaluation_run_id', 'risk_run_id', 'trust_calibration_run_id', 'policy_tuning_run_id'):
        value = plan_metadata.get(key)
        if isinstance(value, int):
            linked_context[key] = value

    return {
        'drift_flags': drift_flags,
        'risk_flags': risk_flags,
        'calibration_flags': calibration_flags,
        'linked_context': linked_context,
    }

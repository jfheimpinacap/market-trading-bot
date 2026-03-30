from apps.evaluation_lab.models import EffectivenessMetricType


def detect_drift_flags(*, metrics, buckets) -> list[dict]:
    flags: list[dict] = []

    for bucket in buckets:
        if bucket.segment_scope != 'global' and bucket.sample_count >= 5 and bucket.calibration_gap >= 0.2:
            flags.append(
                {
                    'flag_type': 'CALIBRATION_DRIFT',
                    'scope': bucket.segment_scope,
                    'segment_value': bucket.segment_value,
                    'value': str(bucket.calibration_gap),
                    'reason': 'Segment calibration gap exceeds threshold.',
                }
            )

    for metric in metrics:
        if metric.metric_type in {
            EffectivenessMetricType.PROVIDER_BIAS_INDICATOR,
            EffectivenessMetricType.CATEGORY_BIAS_INDICATOR,
            EffectivenessMetricType.MODEL_MODE_DRIFT_INDICATOR,
        } and metric.sample_count >= 5 and metric.metric_value >= 0.2:
            flags.append(
                {
                    'flag_type': metric.metric_type.upper(),
                    'scope': metric.metric_scope,
                    'segment_value': metric.metadata.get('segment_value', 'unknown'),
                    'value': str(metric.metric_value),
                    'reason': 'Segment indicator exceeded drift/bias guardrail.',
                }
            )

    return flags

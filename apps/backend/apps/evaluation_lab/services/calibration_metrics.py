import math
from collections import defaultdict
from decimal import Decimal

from apps.evaluation_lab.models import CalibrationBucket, EvaluationSegmentScope


def _bucket_label(probability: Decimal) -> str:
    base = max(min(float(probability), 0.9999), 0.0)
    lower = math.floor(base * 10) / 10
    upper = min(lower + 0.1, 1.0)
    return f'{lower:.1f}-{upper:.1f}'


def _build_bucket_rows(records, segment_scope: str, segment_value: str = '') -> list[dict]:
    grouped: dict[str, list] = defaultdict(list)
    for row in records:
        probability = row.calibrated_probability_at_decision
        realized = row.realized_result_score
        if probability is None or realized is None:
            continue
        grouped[_bucket_label(probability)].append(row)

    built = []
    for label, sample in sorted(grouped.items()):
        probs = [Decimal(item.calibrated_probability_at_decision) for item in sample]
        outcomes = [Decimal(item.realized_result_score) for item in sample]
        count = len(sample)
        mean_prob = sum(probs) / count
        hit_rate = sum(outcomes) / count
        gaps = [abs(p - o) for p, o in zip(probs, outcomes)]
        brier_values = [(p - o) ** 2 for p, o in zip(probs, outcomes)]
        log_loss_values = [
            Decimal(str(-(float(o) * math.log(max(float(p), 1e-6)) + (1 - float(o)) * math.log(max(1 - float(p), 1e-6)))))
            for p, o in zip(probs, outcomes)
        ]
        built.append(
            {
                'bucket_label': label,
                'sample_count': count,
                'mean_predicted_probability': mean_prob.quantize(Decimal('0.0001')),
                'empirical_hit_rate': hit_rate.quantize(Decimal('0.0001')),
                'calibration_gap': (sum(gaps) / count).quantize(Decimal('0.0001')),
                'brier_component': (sum(brier_values) / count).quantize(Decimal('0.0001')),
                'log_loss_component': (sum(log_loss_values) / count).quantize(Decimal('0.00001')),
                'segment_scope': segment_scope,
                'segment_value': segment_value,
                'metadata': {},
            }
        )
    return built


def build_calibration_buckets(*, runtime_run, outcome_records) -> list[CalibrationBucket]:
    payloads = []
    payloads.extend(_build_bucket_rows(outcome_records, EvaluationSegmentScope.GLOBAL, 'global'))

    for scope in [EvaluationSegmentScope.PROVIDER, EvaluationSegmentScope.CATEGORY, EvaluationSegmentScope.HORIZON_BAND, EvaluationSegmentScope.MODEL_MODE]:
        values = sorted({(row.metadata or {}).get(scope, 'unknown') for row in outcome_records})
        for value in values:
            scoped = [row for row in outcome_records if (row.metadata or {}).get(scope, 'unknown') == value]
            payloads.extend(_build_bucket_rows(scoped, scope, str(value)))

    return [CalibrationBucket.objects.create(run=runtime_run, **payload) for payload in payloads]

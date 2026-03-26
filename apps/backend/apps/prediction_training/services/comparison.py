from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from django.utils import timezone

from apps.markets.models import Market, MarketSourceType
from apps.prediction_agent.services.calibration import apply_linear_calibration, clamp_probability, q4
from apps.prediction_agent.services.profiles import get_prediction_profile
from apps.prediction_training.models import (
    ModelComparisonResult,
    ModelComparisonRun,
    ModelComparisonScope,
    ModelComparisonStatus,
    PredictionDatasetRun,
    PredictionModelArtifact,
)
from apps.prediction_training.services.dataset import FEATURE_COLUMNS
from apps.prediction_training.services.evaluation import EvaluationProfileConfig
from apps.prediction_training.services.registry import get_active_model_artifact, predict_probability


@dataclass
class PredictorSpec:
    key: str
    predictor_type: str
    label: str
    profile_slug: str = ''
    artifact: PredictionModelArtifact | None = None


def _parse_dataset_rows(dataset_run: PredictionDatasetRun) -> list[dict]:
    rows: list[dict] = []
    with Path(dataset_run.artifact_path).open('r', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row['label'] = int(row['label'])
            row['market_id'] = int(row.get('market_id') or 0)
            rows.append(row)
    return rows


def _scope_filter(rows: list[dict], scope: str) -> list[dict]:
    if scope == ModelComparisonScope.MIXED:
        return rows
    market_ids = {row['market_id'] for row in rows if row['market_id']}
    source_by_market = {item['id']: item['source_type'] for item in Market.objects.filter(id__in=market_ids).values('id', 'source_type')}
    if scope == ModelComparisonScope.REAL_ONLY:
        return [row for row in rows if source_by_market.get(row['market_id']) == MarketSourceType.REAL_READ_ONLY]
    return [row for row in rows if source_by_market.get(row['market_id']) == MarketSourceType.DEMO]


def _spec_from_key(key: str) -> PredictorSpec:
    if key in {'heuristic_baseline', 'narrative_weighted', 'market_momentum_weighted'}:
        return PredictorSpec(key=key, predictor_type='heuristic_profile', label=key, profile_slug=key)
    if key == 'active_model':
        artifact = get_active_model_artifact()
        if artifact is None:
            raise ValueError('No active model artifact is available.')
        return PredictorSpec(key=f'artifact:{artifact.id}', predictor_type='trained_artifact', label=f'{artifact.name}:{artifact.version}', artifact=artifact)
    if key.startswith('artifact:'):
        artifact_id = int(key.split(':', 1)[1])
        artifact = PredictionModelArtifact.objects.filter(id=artifact_id).first()
        if artifact is None:
            raise ValueError(f'Model artifact {artifact_id} not found.')
        return PredictorSpec(key=key, predictor_type='trained_artifact', label=f'{artifact.name}:{artifact.version}', artifact=artifact)
    raise ValueError(f'Unsupported model key: {key}')


def _heuristic_probability(row: dict, profile_slug: str) -> float:
    profile = get_prediction_profile(profile_slug)
    weights = profile.weights or {}
    market_probability = clamp_probability(Decimal(str(row.get('market_probability', 0.5))))
    momentum_probability = clamp_probability(market_probability + Decimal(str(row.get('recent_snapshot_delta', 0.0))))
    narrative_probability = Decimal(str(row.get('narrative_sentiment_probability', 0.5))) if profile.use_narrative else Decimal('0.5000')
    relevance = Decimal('0.0000')
    learning_delta = Decimal('0.0000') if not profile.use_learning else Decimal('0.0000')
    raw = (
        market_probability * Decimal(str(weights.get('market_anchor', 0.55)))
        + momentum_probability * Decimal(str(weights.get('momentum', 0.20)))
        + narrative_probability * Decimal(str(weights.get('narrative', 0.15 if profile.use_narrative else 0.0)))
        + relevance * Decimal(str(weights.get('relevance', 0.05 if profile.use_narrative else 0.0)))
        + (market_probability + learning_delta) * Decimal(str(weights.get('learning', 0.05 if profile.use_learning else 0.0)))
    )
    return float(apply_linear_calibration(probability=clamp_probability(raw), alpha=profile.calibration_alpha, beta=profile.calibration_beta))


def _predict_probability(row: dict, spec: PredictorSpec) -> float:
    if spec.predictor_type == 'heuristic_profile':
        return _heuristic_probability(row, spec.profile_slug)
    features = [float(row[column]) for column in FEATURE_COLUMNS]
    return float(predict_probability(artifact=spec.artifact, features=features).probability)


def _expected_calibration_error(labels: list[int], probabilities: list[float], bins: int = 10) -> float:
    total = len(labels)
    if total == 0:
        return 0.0
    ece = 0.0
    for idx in range(bins):
        low = idx / bins
        high = (idx + 1) / bins
        bucket = [i for i, p in enumerate(probabilities) if (p >= low and p < high) or (idx == bins - 1 and p == 1.0)]
        if not bucket:
            continue
        bucket_acc = sum(labels[i] for i in bucket) / len(bucket)
        bucket_conf = sum(probabilities[i] for i in bucket) / len(bucket)
        ece += (len(bucket) / total) * abs(bucket_acc - bucket_conf)
    return ece


def _build_metrics(labels: list[int], market_probabilities: list[float], probabilities: list[float], failures: int, total_rows: int) -> dict:
    if not labels:
        return {
            'accuracy': 0.0,
            'log_loss': 99.0,
            'brier_score': 99.0,
            'calibration_error': 1.0,
            'coverage': 0.0,
            'failure_count': failures,
            'average_edge_magnitude': 0.0,
            'edge_hit_rate': 0.0,
            'direction_correctness': 0.0,
            'confidence_usefulness': 0.0,
        }
    preds = [1 if p >= 0.5 else 0 for p in probabilities]
    correct = sum(1 for idx, pred in enumerate(preds) if pred == labels[idx])
    accuracy = correct / len(labels)
    eps = 1e-15
    clipped_probs = [min(max(p, eps), 1 - eps) for p in probabilities]
    logloss = -sum((labels[i] * math.log(clipped_probs[i])) + ((1 - labels[i]) * math.log(1 - clipped_probs[i])) for i in range(len(labels))) / len(labels)
    brier = sum((clipped_probs[i] - labels[i]) ** 2 for i in range(len(labels))) / len(labels)
    edges = [q4(Decimal(str(probabilities[i])) - Decimal(str(market_probabilities[i]))) for i in range(len(labels))]
    hits = [1 if ((edges[i] >= 0 and labels[i] == 1) or (edges[i] < 0 and labels[i] == 0)) else 0 for i in range(len(labels))]
    confidence_useful = [1 if abs(edges[i]) >= Decimal('0.03') and hits[i] == 1 else 0 for i in range(len(labels))]
    return {
        'accuracy': round(float(accuracy), 6),
        'log_loss': round(float(logloss), 6),
        'brier_score': round(float(brier), 6),
        'calibration_error': round(float(_expected_calibration_error(labels, probabilities)), 6),
        'coverage': round(len(labels) / max(total_rows, 1), 6),
        'failure_count': failures,
        'average_edge_magnitude': round(sum(abs(float(edge)) for edge in edges) / len(edges), 6),
        'edge_hit_rate': round(sum(hits) / len(hits), 6),
        'direction_correctness': round(sum(hits) / len(hits), 6),
        'confidence_usefulness': round(sum(confidence_useful) / len(confidence_useful), 6),
    }


def _score_from_profile(metrics: dict, config: dict) -> float:
    weights = config.get('weights', {})
    return (
        (metrics['accuracy'] * float(weights.get('accuracy', 0.2)))
        + ((1.0 - min(metrics['log_loss'], 1.0)) * float(weights.get('log_loss', 0.2)))
        + ((1.0 - min(metrics['brier_score'], 1.0)) * float(weights.get('brier_score', 0.2)))
        + ((1.0 - min(metrics['calibration_error'], 1.0)) * float(weights.get('calibration_error', 0.2)))
        + (metrics['edge_hit_rate'] * float(weights.get('edge_hit_rate', 0.1)))
        + (metrics['confidence_usefulness'] * float(weights.get('confidence_usefulness', 0.1)))
    )


def run_model_comparison(*, baseline_key: str, candidate_key: str, profile: EvaluationProfileConfig, scope: str, dataset_run: PredictionDatasetRun, replay_run_id: int | None = None) -> ModelComparisonRun:
    started_at = timezone.now()
    run = ModelComparisonRun.objects.create(
        status=ModelComparisonStatus.RUNNING,
        scope=scope,
        evaluation_profile=profile.profile,
        dataset_run=dataset_run,
        replay_run_id=replay_run_id,
        baseline_key=baseline_key,
        candidate_key=candidate_key,
        started_at=started_at,
    )
    try:
        scoped_rows = _scope_filter(_parse_dataset_rows(dataset_run), scope)
        baseline_spec = _spec_from_key(baseline_key)
        candidate_spec = _spec_from_key(candidate_key)

        per_predictor: dict[str, dict] = {}
        for spec in (baseline_spec, candidate_spec):
            labels: list[int] = []
            market_probs: list[float] = []
            probs: list[float] = []
            failures = 0
            for row in scoped_rows:
                try:
                    prob = _predict_probability(row, spec)
                    labels.append(int(row['label']))
                    market_probs.append(float(row.get('market_probability', 0.5)))
                    probs.append(max(0.0, min(1.0, prob)))
                except Exception:
                    failures += 1
            metrics = _build_metrics(labels, market_probs, probs, failures, len(scoped_rows))
            result = ModelComparisonResult.objects.create(
                run=run,
                predictor_key=spec.key,
                predictor_label=spec.label,
                predictor_type=spec.predictor_type,
                profile_slug=spec.profile_slug,
                artifact=spec.artifact,
                metrics=metrics,
                failures=failures,
                coverage=Decimal(str(metrics['coverage'])),
            )
            per_predictor[spec.key] = {'metrics': metrics, 'result_id': result.id}

        baseline_metrics = per_predictor[baseline_spec.key]['metrics']
        candidate_metrics = per_predictor[candidate_spec.key]['metrics']
        baseline_score = _score_from_profile(baseline_metrics, profile.config)
        candidate_score = _score_from_profile(candidate_metrics, profile.config)

        run.metrics_summary = {
            'baseline_score': round(baseline_score, 6),
            'candidate_score': round(candidate_score, 6),
            'score_delta': round(candidate_score - baseline_score, 6),
            'rows_evaluated': len(scoped_rows),
        }
        run.details = {'baseline_metrics': baseline_metrics, 'candidate_metrics': candidate_metrics}
        run.summary = f'Compared {baseline_key} vs {candidate_key} on {len(scoped_rows)} rows ({scope}).'
        run.status = ModelComparisonStatus.SUCCESS
        run.finished_at = timezone.now()
        run.save(update_fields=['metrics_summary', 'details', 'summary', 'status', 'finished_at', 'updated_at'])
    except Exception as exc:
        run.status = ModelComparisonStatus.FAILED
        run.finished_at = timezone.now()
        run.summary = f'Comparison failed: {exc}'
        run.details = {'error': str(exc)}
        run.save(update_fields=['status', 'finished_at', 'summary', 'details', 'updated_at'])
        raise
    return run

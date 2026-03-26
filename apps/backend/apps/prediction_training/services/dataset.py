from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone

from apps.markets.models import Market, MarketSnapshot
from apps.prediction_agent.services.features import _sentiment_to_probability
from apps.prediction_training.models import PredictionDatasetRun, PredictionTrainingStatus
from apps.research_agent.models import ResearchCandidate


DATASET_LABEL = 'future_probability_up_24h'
FEATURE_SET_VERSION = 'prediction_features_v1'
FEATURE_COLUMNS = [
    'market_probability',
    'recent_snapshot_delta',
    'time_to_resolution_hours',
    'volume_24h',
    'liquidity',
    'narrative_sentiment_probability',
    'narrative_confidence',
    'divergence_score',
]


@dataclass
class DatasetBuildResult:
    dataset_run: PredictionDatasetRun


def _artifact_root() -> Path:
    base = Path(settings.BASE_DIR) / 'artifacts' / 'prediction_training'
    base.mkdir(parents=True, exist_ok=True)
    return base


def _to_float(value: Decimal | None, fallback: float = 0.0) -> float:
    if value is None:
        return fallback
    return float(value)


def _market_queryset() -> QuerySet[Market]:
    return Market.objects.filter(outcome_type='yes_no').select_related('provider')


def _candidate_by_market() -> dict[int, ResearchCandidate]:
    items = ResearchCandidate.objects.order_by('market_id', '-updated_at', '-id')
    by_market: dict[int, ResearchCandidate] = {}
    for item in items:
        if item.market_id not in by_market:
            by_market[item.market_id] = item
    return by_market


def build_prediction_dataset(*, name: str = 'default_dataset', horizon_hours: int = 24) -> DatasetBuildResult:
    started_at = timezone.now()
    dataset_run = PredictionDatasetRun.objects.create(
        name=name,
        status=PredictionTrainingStatus.RUNNING,
        label_definition=DATASET_LABEL,
        feature_set_version=FEATURE_SET_VERSION,
        snapshot_horizon_hours=horizon_hours,
        started_at=started_at,
        details={},
    )

    rows: list[dict] = []
    period_start = None
    period_end = None
    horizon = timedelta(hours=horizon_hours)
    candidates = _candidate_by_market()

    try:
        for market in _market_queryset().iterator():
            candidate = candidates.get(market.id)
            snapshots = list(MarketSnapshot.objects.filter(market=market).order_by('captured_at', 'id'))
            if len(snapshots) < 2:
                continue

            for idx, snapshot in enumerate(snapshots):
                if snapshot.market_probability is None:
                    continue
                future_cutoff = snapshot.captured_at + horizon
                future = next((item for item in snapshots[idx + 1 :] if item.captured_at >= future_cutoff and item.market_probability is not None), None)
                if future is None:
                    continue
                previous = snapshots[idx - 1] if idx > 0 else None
                momentum = Decimal('0.0000')
                if previous and previous.market_probability is not None:
                    momentum = Decimal(str(snapshot.market_probability)) - Decimal(str(previous.market_probability))
                time_to_resolution_hours = Decimal('0.00')
                if market.resolution_time:
                    delta_seconds = max((market.resolution_time - snapshot.captured_at).total_seconds(), 0)
                    time_to_resolution_hours = Decimal(delta_seconds / 3600).quantize(Decimal('0.01'))

                narrative_sentiment_probability = Decimal('0.5000')
                narrative_confidence = Decimal('0.0000')
                divergence_score = Decimal('0.0000')
                if candidate:
                    narrative_sentiment_probability = _sentiment_to_probability(candidate.sentiment_direction)
                    narrative_confidence = Decimal(str(candidate.narrative_pressure or Decimal('0.0000')))
                    divergence_score = Decimal(str(candidate.divergence_score or Decimal('0.0000')))

                row = {
                    'market_id': market.id,
                    'snapshot_id': snapshot.id,
                    'captured_at': snapshot.captured_at.isoformat(),
                    'label': int(Decimal(str(future.market_probability)) > Decimal(str(snapshot.market_probability))),
                    'market_probability': _to_float(snapshot.market_probability, 0.5),
                    'recent_snapshot_delta': float(momentum),
                    'time_to_resolution_hours': float(time_to_resolution_hours),
                    'volume_24h': _to_float(snapshot.volume_24h, 0.0),
                    'liquidity': _to_float(snapshot.liquidity, 0.0),
                    'narrative_sentiment_probability': float(narrative_sentiment_probability),
                    'narrative_confidence': float(narrative_confidence),
                    'divergence_score': float(divergence_score),
                    'future_probability': _to_float(future.market_probability, 0.5),
                }
                rows.append(row)
                if period_start is None or snapshot.captured_at < period_start:
                    period_start = snapshot.captured_at
                if period_end is None or snapshot.captured_at > period_end:
                    period_end = snapshot.captured_at

        artifact_root = _artifact_root()
        dataset_path = artifact_root / f'dataset_run_{dataset_run.id}.csv'
        with dataset_path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ['label'])
            writer.writeheader()
            writer.writerows(rows)

        positives = sum(1 for row in rows if row['label'] == 1)
        negatives = len(rows) - positives
        dataset_run.status = PredictionTrainingStatus.SUCCESS
        dataset_run.rows_built = len(rows)
        dataset_run.positive_rows = positives
        dataset_run.negative_rows = negatives
        dataset_run.period_start = period_start
        dataset_run.period_end = period_end
        dataset_run.feature_names = FEATURE_COLUMNS
        dataset_run.artifact_path = str(dataset_path)
        dataset_run.finished_at = timezone.now()
        dataset_run.summary = f'Built {len(rows)} rows for label={DATASET_LABEL} at horizon={horizon_hours}h.'
        dataset_run.details = {
            'label': DATASET_LABEL,
            'feature_set_version': FEATURE_SET_VERSION,
            'min_rows_for_training': 30,
        }
        dataset_run.save()
    except Exception as exc:  # pragma: no cover - defensive
        dataset_run.status = PredictionTrainingStatus.FAILED
        dataset_run.finished_at = timezone.now()
        dataset_run.summary = f'Dataset build failed: {exc}'
        dataset_run.details = {'error': str(exc)}
        dataset_run.save(update_fields=['status', 'finished_at', 'summary', 'details', 'updated_at'])
        raise

    return DatasetBuildResult(dataset_run=dataset_run)

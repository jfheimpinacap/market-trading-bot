from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from apps.markets.models import Market
from apps.prediction_agent.models import (
    PredictionConfidenceLevel,
    PredictionFeatureSnapshot,
    PredictionModelProfile,
    PredictionRun,
    PredictionRunStatus,
    PredictionScore,
)
from apps.prediction_agent.services.calibration import (
    apply_linear_calibration,
    classify_edge,
    clamp_probability,
    confidence_level,
    q4,
)
from apps.prediction_agent.services.features import build_prediction_features
from apps.prediction_agent.services.precedent_enrichment import apply_prediction_precedents
from apps.prediction_agent.services.profiles import get_prediction_profile
from apps.prediction_training.services.dataset import FEATURE_COLUMNS
from apps.prediction_training.services.registry import get_active_model_artifact, predict_probability


@dataclass
class ScoringResult:
    run: PredictionRun
    score: PredictionScore


def _safe_decimal(snapshot: dict, key: str, default: str = '0.0000') -> Decimal:
    return Decimal(str(snapshot.get(key, default)))


def _build_model_feature_vector(snapshot: dict) -> list[float]:
    return [float(snapshot.get(column, 0.0) or 0.0) for column in FEATURE_COLUMNS]


def score_market_prediction(*, market: Market, profile_slug: str | None = None, triggered_by: str = 'api') -> ScoringResult:
    profile = get_prediction_profile(profile_slug)
    started_at = timezone.now()
    run = PredictionRun.objects.create(
        status=PredictionRunStatus.SUCCESS,
        triggered_by=triggered_by,
        model_profile=profile,
        started_at=started_at,
        metadata={'profile_slug': profile.slug},
    )

    feature_result = build_prediction_features(market=market)
    snapshot = feature_result.snapshot

    feature_snapshot = PredictionFeatureSnapshot.objects.create(
        run=run,
        market=market,
        snapshot=snapshot,
        source_type=market.source_type,
        provider_slug=market.provider.slug,
        stale_market_data=feature_result.stale_market_data,
    )

    market_probability = clamp_probability(_safe_decimal(snapshot, 'market_probability', '0.5000'))
    momentum_delta = _safe_decimal(snapshot, 'recent_snapshot_delta')
    narrative_probability = _safe_decimal(snapshot, 'narrative_sentiment_probability', '0.5000')
    narrative_confidence = _safe_decimal(snapshot, 'narrative_confidence')
    relevance = _safe_decimal(snapshot, 'market_relevance_score')
    learning_confidence_delta = _safe_decimal(snapshot, 'learning_confidence_delta') if profile.use_learning else Decimal('0.0000')

    weights = profile.weights or {}
    market_anchor_weight = Decimal(str(weights.get('market_anchor', 0.55)))
    momentum_weight = Decimal(str(weights.get('momentum', 0.20)))
    narrative_weight = Decimal(str(weights.get('narrative', 0.15))) if profile.use_narrative else Decimal('0.0000')
    relevance_weight = Decimal(str(weights.get('relevance', 0.05))) if profile.use_narrative else Decimal('0.0000')
    learning_weight = Decimal(str(weights.get('learning', 0.05))) if profile.use_learning else Decimal('0.0000')

    momentum_probability = clamp_probability(market_probability + momentum_delta)

    raw_probability = (
        (market_probability * market_anchor_weight)
        + (momentum_probability * momentum_weight)
        + (narrative_probability * narrative_weight)
        + (relevance * relevance_weight)
        + ((market_probability + learning_confidence_delta) * learning_weight)
    )
    heuristic_system_probability = apply_linear_calibration(
        probability=clamp_probability(raw_probability),
        alpha=profile.calibration_alpha,
        beta=profile.calibration_beta,
    )

    system_probability = heuristic_system_probability
    model_profile_used = profile.slug
    model_details = {
        'runtime_mode': 'heuristic_fallback',
    }
    active_artifact = get_active_model_artifact()
    if active_artifact is not None:
        try:
            trained_prediction = predict_probability(artifact=active_artifact, features=_build_model_feature_vector(snapshot))
            system_probability = clamp_probability(trained_prediction.probability)
            model_profile_used = f'trained:{trained_prediction.artifact.name}:{trained_prediction.artifact.version}'
            model_details = {
                'runtime_mode': 'trained_model',
                'artifact_id': trained_prediction.artifact.id,
                'artifact_name': trained_prediction.artifact.name,
                'artifact_version': trained_prediction.artifact.version,
                'artifact_model_type': trained_prediction.artifact.model_type,
            }
        except Exception as exc:
            model_details = {
                'runtime_mode': 'heuristic_fallback_model_error',
                'error': str(exc),
            }

    edge = q4(system_probability - market_probability)

    base_confidence = Decimal('0.3500')
    confidence = base_confidence + min(abs(edge) * Decimal('2.20'), Decimal('0.3000'))
    confidence += min(narrative_confidence * Decimal('0.25'), Decimal('0.1500')) if profile.use_narrative else Decimal('0.0000')
    confidence -= Decimal('0.1200') if feature_result.stale_market_data else Decimal('0.0000')
    confidence = max(profile.confidence_floor, min(profile.confidence_cap, q4(confidence)))

    edge_label = classify_edge(edge, strong_threshold=profile.edge_strong_threshold, neutral_threshold=profile.edge_neutral_threshold)
    conf_level = confidence_level(confidence)

    rationale = (
        f"Mode={model_details.get('runtime_mode')}. system_probability={system_probability}, market_probability={market_probability}, edge={edge}. "
        f"Heuristic_baseline={heuristic_system_probability}. Inputs: momentum_delta={momentum_delta}, "
        f"narrative_probability={narrative_probability if profile.use_narrative else 'disabled'}, "
        f"narrative_confidence={narrative_confidence if profile.use_narrative else 'disabled'}, stale_market_data={feature_result.stale_market_data}."
    )

    score = PredictionScore.objects.create(
        run=run,
        market=market,
        model_profile=profile,
        feature_snapshot=feature_snapshot,
        market_probability=market_probability,
        system_probability=system_probability,
        edge=edge,
        confidence=confidence,
        confidence_level=conf_level if conf_level in PredictionConfidenceLevel.values else PredictionConfidenceLevel.MEDIUM,
        edge_label=edge_label,
        rationale=rationale,
        narrative_contribution=q4((narrative_probability - market_probability) * narrative_weight),
        model_profile_used=model_profile_used,
        details={
            'weights': weights,
            'market_anchor_weight': str(market_anchor_weight),
            'momentum_weight': str(momentum_weight),
            'narrative_weight': str(narrative_weight),
            'relevance_weight': str(relevance_weight),
            'learning_weight': str(learning_weight),
            'triggered_by': triggered_by,
            'model_runtime': model_details,
        },
    )
    adjusted_confidence, precedent_note, precedent_context = apply_prediction_precedents(
        score=score,
        system_probability=system_probability,
        confidence=confidence,
    )
    score.confidence = max(profile.confidence_floor, min(profile.confidence_cap, adjusted_confidence))
    score.confidence_level = confidence_level(score.confidence)
    score.rationale = f'{score.rationale} Precedent context: {precedent_note}'
    score.details = {
        **(score.details or {}),
        'precedent_context': precedent_context,
    }
    score.save(update_fields=['confidence', 'confidence_level', 'rationale', 'details', 'updated_at'])

    run.finished_at = timezone.now()
    run.markets_scored = 1
    run.save(update_fields=['finished_at', 'markets_scored', 'updated_at'])

    return ScoringResult(run=run, score=score)

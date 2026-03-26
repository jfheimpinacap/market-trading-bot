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
from apps.prediction_agent.services.profiles import get_prediction_profile


@dataclass
class ScoringResult:
    run: PredictionRun
    score: PredictionScore


def _safe_decimal(snapshot: dict, key: str, default: str = '0.0000') -> Decimal:
    return Decimal(str(snapshot.get(key, default)))


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
    system_probability = apply_linear_calibration(
        probability=clamp_probability(raw_probability),
        alpha=profile.calibration_alpha,
        beta=profile.calibration_beta,
    )

    edge = q4(system_probability - market_probability)

    base_confidence = Decimal('0.3500')
    confidence = base_confidence + min(abs(edge) * Decimal('2.20'), Decimal('0.3000'))
    confidence += min(narrative_confidence * Decimal('0.25'), Decimal('0.1500')) if profile.use_narrative else Decimal('0.0000')
    confidence -= Decimal('0.1200') if feature_result.stale_market_data else Decimal('0.0000')
    confidence = max(profile.confidence_floor, min(profile.confidence_cap, q4(confidence)))

    edge_label = classify_edge(edge, strong_threshold=profile.edge_strong_threshold, neutral_threshold=profile.edge_neutral_threshold)
    conf_level = confidence_level(confidence)

    rationale = (
        f"Profile={profile.slug}. system_probability={system_probability}, market_probability={market_probability}, edge={edge}. "
        f"Inputs: momentum_delta={momentum_delta}, narrative_probability={narrative_probability if profile.use_narrative else 'disabled'}, "
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
        model_profile_used=profile.slug,
        details={
            'weights': weights,
            'market_anchor_weight': str(market_anchor_weight),
            'momentum_weight': str(momentum_weight),
            'narrative_weight': str(narrative_weight),
            'relevance_weight': str(relevance_weight),
            'learning_weight': str(learning_weight),
            'triggered_by': triggered_by,
        },
    )

    run.finished_at = timezone.now()
    run.markets_scored = 1
    run.save(update_fields=['finished_at', 'markets_scored', 'updated_at'])

    return ScoringResult(run=run, score=score)

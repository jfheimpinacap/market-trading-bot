from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from apps.learning_memory.services import build_learning_influence
from apps.learning_memory.services.application import record_application_for_component
from apps.markets.models import Market, MarketSnapshot
from apps.research_agent.models import NarrativeSentiment, ResearchCandidate


@dataclass
class FeatureBuildResult:
    snapshot: dict
    stale_market_data: bool


def _sentiment_to_probability(sentiment: str) -> Decimal:
    mapping = {
        NarrativeSentiment.BULLISH: Decimal('0.7000'),
        NarrativeSentiment.BEARISH: Decimal('0.3000'),
        NarrativeSentiment.NEUTRAL: Decimal('0.5000'),
        NarrativeSentiment.MIXED: Decimal('0.5000'),
        NarrativeSentiment.UNCERTAIN: Decimal('0.5000'),
    }
    return mapping.get(sentiment, Decimal('0.5000'))


def build_prediction_features(*, market: Market) -> FeatureBuildResult:
    latest_snapshot = MarketSnapshot.objects.filter(market=market).order_by('-captured_at', '-id').first()
    previous_snapshot = MarketSnapshot.objects.filter(market=market).order_by('-captured_at', '-id')[1:2].first()

    market_probability = market.current_market_probability
    if market_probability is None and latest_snapshot and latest_snapshot.market_probability is not None:
        market_probability = latest_snapshot.market_probability
    market_probability = Decimal(str(market_probability if market_probability is not None else Decimal('0.5000')))

    momentum_delta = Decimal('0.0000')
    if latest_snapshot and previous_snapshot and latest_snapshot.market_probability is not None and previous_snapshot.market_probability is not None:
        momentum_delta = Decimal(str(latest_snapshot.market_probability)) - Decimal(str(previous_snapshot.market_probability))

    now = timezone.now()
    time_to_resolution_hours = Decimal('0')
    if market.resolution_time:
        delta = market.resolution_time - now
        time_to_resolution_hours = Decimal(max(delta.total_seconds(), 0) / 3600)

    candidate = ResearchCandidate.objects.filter(market=market).order_by('-updated_at', '-id').first()
    narrative_sentiment_probability = Decimal('0.5000')
    narrative_confidence = Decimal('0.0000')
    market_relevance_score = Decimal('0.0000')
    divergence_score = Decimal('0.0000')

    if candidate:
        narrative_sentiment_probability = _sentiment_to_probability(candidate.sentiment_direction)
        narrative_confidence = Decimal(str(candidate.narrative_pressure or Decimal('0.0000')))
        divergence_score = Decimal(str(candidate.divergence_score or Decimal('0.0000')))
        analysis_values = [
            item.analysis.market_relevance_score
            for item in candidate.narrative_items.select_related('analysis').all()
            if getattr(item, 'analysis', None) is not None
        ]
        if analysis_values:
            market_relevance_score = sum((Decimal(str(value)) for value in analysis_values), Decimal('0.0000')) / Decimal(len(analysis_values))

    record_application_for_component(target_component='prediction', target_entity_id=str(market.id))
    learning_influence = build_learning_influence(market=market, source_type=market.source_type)

    stale_market_data = True
    provider_freshness_minutes = Decimal('99999.0')
    if latest_snapshot:
        provider_freshness_minutes = Decimal((now - latest_snapshot.captured_at).total_seconds() / 60)
        stale_market_data = provider_freshness_minutes > Decimal('120')

    snapshot = {
        'market_probability': str(market_probability),
        'yes_price': str(market.current_yes_price or Decimal('0.0000')),
        'no_price': str(market.current_no_price or Decimal('0.0000')),
        'liquidity': str(market.liquidity or Decimal('0.0000')),
        'volume_24h': str(market.volume_24h or Decimal('0.0000')),
        'volume_total': str(market.volume_total or Decimal('0.0000')),
        'time_to_resolution_hours': str(time_to_resolution_hours.quantize(Decimal('0.01'))),
        'recent_snapshot_delta': str(momentum_delta.quantize(Decimal('0.0001'))),
        'source_type': market.source_type,
        'provider': market.provider.slug,
        'narrative_sentiment_probability': str(narrative_sentiment_probability),
        'narrative_confidence': str(narrative_confidence),
        'market_relevance_score': str(market_relevance_score.quantize(Decimal('0.0001'))),
        'divergence_narrative_vs_market': str((narrative_sentiment_probability - market_probability).quantize(Decimal('0.0001'))),
        'divergence_score': str(divergence_score),
        'learning_confidence_delta': str(learning_influence.confidence_delta),
        'learning_quantity_multiplier': str(learning_influence.quantity_multiplier),
        'provider_freshness_minutes': str(provider_freshness_minutes.quantize(Decimal('0.1'))),
        'stale_market_data': stale_market_data,
    }

    return FeatureBuildResult(snapshot=snapshot, stale_market_data=stale_market_data)

from __future__ import annotations

from decimal import Decimal

from django.db.models import Avg, Count

from apps.research_agent.models import (
    MarketNarrativeLink,
    NarrativeMarketRelation,
    NarrativeSentiment,
    ResearchCandidate,
)


def _sentiment_to_pressure(sentiment: str) -> Decimal:
    mapping = {
        NarrativeSentiment.BULLISH: Decimal('0.80'),
        NarrativeSentiment.BEARISH: Decimal('-0.80'),
        NarrativeSentiment.NEUTRAL: Decimal('0.00'),
        NarrativeSentiment.MIXED: Decimal('0.15'),
        NarrativeSentiment.UNCERTAIN: Decimal('0.00'),
    }
    return mapping.get(sentiment, Decimal('0.00'))


def _market_implied_direction(probability: Decimal | None) -> str:
    if probability is None:
        return NarrativeSentiment.UNCERTAIN
    if probability >= Decimal('0.55'):
        return NarrativeSentiment.BULLISH
    if probability <= Decimal('0.45'):
        return NarrativeSentiment.BEARISH
    return NarrativeSentiment.NEUTRAL


def generate_research_candidates() -> int:
    grouped = (
        MarketNarrativeLink.objects.select_related('narrative_item__analysis', 'market')
        .values('market_id')
        .annotate(item_count=Count('narrative_item_id'), avg_strength=Avg('link_strength'))
    )

    count = 0
    for group in grouped:
        links = MarketNarrativeLink.objects.select_related('narrative_item__analysis', 'market').filter(market_id=group['market_id'])
        market = links.first().market
        sentiment_pressure = Decimal('0.0000')
        confidence_sum = Decimal('0.0000')
        best_summary = ''
        narrative_items = []

        for link in links:
            analysis = getattr(link.narrative_item, 'analysis', None)
            if not analysis:
                continue
            sentiment_pressure += (_sentiment_to_pressure(analysis.sentiment) * link.link_strength)
            confidence_sum += analysis.confidence
            best_summary = best_summary or analysis.summary
            narrative_items.append(link.narrative_item)

        item_count = max(len(narrative_items), 1)
        narrative_pressure = (sentiment_pressure / Decimal(item_count)).quantize(Decimal('0.0001'))
        avg_confidence = (confidence_sum / Decimal(item_count)).quantize(Decimal('0.0001'))
        implied_probability = market.current_market_probability
        implied_direction = _market_implied_direction(implied_probability)
        narrative_direction = NarrativeSentiment.BULLISH if narrative_pressure > Decimal('0.10') else NarrativeSentiment.BEARISH if narrative_pressure < Decimal('-0.10') else NarrativeSentiment.NEUTRAL

        relation = NarrativeMarketRelation.UNCERTAINTY
        divergence = Decimal('0.2500')
        if narrative_direction == implied_direction and narrative_direction != NarrativeSentiment.NEUTRAL:
            relation = NarrativeMarketRelation.ALIGNMENT
            divergence = Decimal('0.1500')
        elif narrative_direction != implied_direction and implied_direction != NarrativeSentiment.NEUTRAL and narrative_direction != NarrativeSentiment.NEUTRAL:
            relation = NarrativeMarketRelation.DIVERGENCE
            divergence = Decimal('0.8500')

        liquidity_factor = Decimal('0.0')
        if market.liquidity:
            liquidity_factor = min(Decimal(market.liquidity) / Decimal('100000'), Decimal('0.5'))

        priority = (Decimal(abs(narrative_pressure)) * Decimal('40') + divergence * Decimal('40') + avg_confidence * Decimal('20') + liquidity_factor * Decimal('10')).quantize(Decimal('0.01'))
        candidate, _ = ResearchCandidate.objects.update_or_create(
            market=market,
            defaults={
                'narrative_pressure': narrative_pressure,
                'sentiment_direction': narrative_direction,
                'implied_probability_snapshot': implied_probability,
                'market_implied_direction': implied_direction,
                'relation': relation,
                'divergence_score': divergence,
                'short_thesis': (best_summary or f'Narrative scan around {market.title}')[:255],
                'priority': priority,
                'metadata': {
                    'avg_link_strength': float(group['avg_strength'] or 0),
                    'linked_item_count': len(narrative_items),
                },
            },
        )
        candidate.narrative_items.set(narrative_items)
        count += 1

    return count

from __future__ import annotations

from decimal import Decimal

from django.db.models import Avg, Count

from apps.research_agent.models import (
    MarketNarrativeLink,
    NarrativeMarketRelation,
    NarrativeSentiment,
    NarrativeSourceType,
    ResearchCandidate,
)
from apps.research_agent.services.social_fusion import classify_source_mix, social_weight
from apps.research_agent.services.social_normalization import compute_cross_source_agreement, normalize_social_metrics


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
        rss_count = 0
        social_count = 0
        reddit_count = 0
        twitter_count = 0
        social_strength_sum = Decimal('0.0000')
        rss_contribution = Decimal('0.0000')
        social_contribution = Decimal('0.0000')
        source_direction_pressure = {'rss': Decimal('0.0000'), 'reddit': Decimal('0.0000'), 'twitter': Decimal('0.0000')}

        for link in links:
            analysis = getattr(link.narrative_item, 'analysis', None)
            if not analysis:
                continue
            social_signal, hype_risk, noise_risk = normalize_social_metrics(analysis.metadata or {})
            source_type = link.narrative_item.source.source_type
            social_adj_weight = social_weight(
                source_type=source_type,
                hype_risk=float(hype_risk),
                noise_risk=float(noise_risk),
            )
            weighted_strength = (link.link_strength * social_adj_weight).quantize(Decimal('0.0001'))
            weighted_pressure = _sentiment_to_pressure(analysis.sentiment) * weighted_strength
            sentiment_pressure += weighted_pressure
            confidence_sum += analysis.confidence
            best_summary = best_summary or analysis.summary
            narrative_items.append(link.narrative_item)
            if source_type == NarrativeSourceType.REDDIT:
                social_count += 1
                reddit_count += 1
                social_contribution += abs(weighted_pressure)
                social_strength_sum += social_signal
                source_direction_pressure['reddit'] += weighted_pressure
            elif source_type == NarrativeSourceType.TWITTER:
                social_count += 1
                twitter_count += 1
                social_contribution += abs(weighted_pressure)
                social_strength_sum += social_signal
                source_direction_pressure['twitter'] += weighted_pressure
            else:
                rss_count += 1
                rss_contribution += abs(weighted_pressure)
                source_direction_pressure['rss'] += weighted_pressure

        item_count = max(len(narrative_items), 1)
        narrative_pressure = (sentiment_pressure / Decimal(item_count)).quantize(Decimal('0.0001'))
        avg_confidence = (confidence_sum / Decimal(item_count)).quantize(Decimal('0.0001'))
        implied_probability = market.current_market_probability
        implied_direction = _market_implied_direction(implied_probability)
        narrative_direction = NarrativeSentiment.BULLISH if narrative_pressure > Decimal('0.10') else NarrativeSentiment.BEARISH if narrative_pressure < Decimal('-0.10') else NarrativeSentiment.NEUTRAL

        relation = NarrativeMarketRelation.UNCERTAINTY
        divergence = Decimal('0.2500')
        source_convergent = True
        if rss_count and social_count:
            combined_social_pressure = source_direction_pressure['reddit'] + source_direction_pressure['twitter']
            source_convergent = source_direction_pressure['rss'] * combined_social_pressure >= Decimal('0.0')
            if not source_convergent:
                relation = NarrativeMarketRelation.UNCERTAINTY
                divergence = Decimal('0.6200')
        if narrative_direction == implied_direction and narrative_direction != NarrativeSentiment.NEUTRAL:
            relation = NarrativeMarketRelation.ALIGNMENT
            divergence = Decimal('0.1500')
        elif narrative_direction != implied_direction and implied_direction != NarrativeSentiment.NEUTRAL and narrative_direction != NarrativeSentiment.NEUTRAL:
            relation = NarrativeMarketRelation.DIVERGENCE
            divergence = Decimal('0.8500')

        liquidity_factor = Decimal('0.0')
        if market.liquidity:
            liquidity_factor = min(Decimal(market.liquidity) / Decimal('100000'), Decimal('0.5'))

        source_mix = classify_source_mix(
            rss_count=rss_count,
            reddit_count=reddit_count,
            twitter_count=twitter_count,
            convergent=source_convergent,
        )
        cross_agreement, cross_divergence = compute_cross_source_agreement(source_direction_pressure)
        social_confidence_boost = Decimal('0.0')
        if rss_count and social_count and source_convergent:
            social_confidence_boost = Decimal('0.08')
        elif rss_count and social_count and not source_convergent:
            social_confidence_boost = Decimal('-0.12')
        elif social_count and not rss_count:
            social_confidence_boost = Decimal('-0.08')
        adjusted_confidence = min(max(avg_confidence + social_confidence_boost, Decimal('0.0500')), Decimal('0.9800')).quantize(Decimal('0.0001'))

        priority = (
            Decimal(abs(narrative_pressure)) * Decimal('40')
            + divergence * Decimal('40')
            + adjusted_confidence * Decimal('20')
            + liquidity_factor * Decimal('10')
        ).quantize(Decimal('0.01'))
        candidate, _ = ResearchCandidate.objects.update_or_create(
            market=market,
            defaults={
                'narrative_pressure': narrative_pressure,
                'sentiment_direction': narrative_direction,
                'implied_probability_snapshot': implied_probability,
                'market_implied_direction': implied_direction,
                'relation': relation,
                'divergence_score': divergence,
                'rss_narrative_contribution': rss_contribution.quantize(Decimal('0.0001')),
                'social_narrative_contribution': social_contribution.quantize(Decimal('0.0001')),
                'source_mix': source_mix,
                'short_thesis': (best_summary or f'Narrative scan around {market.title}')[:255],
                'priority': priority,
                'metadata': {
                    'avg_link_strength': float(group['avg_strength'] or 0),
                    'linked_item_count': len(narrative_items),
                    'rss_item_count': rss_count,
                    'reddit_item_count': reddit_count,
                    'twitter_item_count': twitter_count,
                    'social_item_count': social_count,
                    'combined_confidence': float(adjusted_confidence),
                    'social_signal_strength_avg': float((social_strength_sum / Decimal(max(social_count, 1))).quantize(Decimal('0.0001'))),
                    'source_convergent': source_convergent,
                    'cross_source_agreement': float(cross_agreement),
                    'cross_source_divergence': float(cross_divergence),
                    'narrative_consistency': 'aligned' if cross_agreement >= Decimal('0.66') else 'conflicted' if cross_divergence >= Decimal('0.66') else 'mixed',
                    'source_contribution': {
                        'rss': float(rss_contribution.quantize(Decimal('0.0001'))),
                        'reddit': float(abs(source_direction_pressure['reddit']).quantize(Decimal('0.0001'))),
                        'twitter': float(abs(source_direction_pressure['twitter']).quantize(Decimal('0.0001'))),
                    },
                },
            },
        )
        candidate.narrative_items.set(narrative_items)
        count += 1

    return count

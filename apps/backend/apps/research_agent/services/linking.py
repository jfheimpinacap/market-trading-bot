from __future__ import annotations

from decimal import Decimal

from django.db.models import Q

from apps.markets.models import Market
from apps.research_agent.models import MarketNarrativeLink, NarrativeAnalysis, NarrativeItem


def _score_market_link(*, item: NarrativeItem, analysis: NarrativeAnalysis, market: Market) -> tuple[Decimal, str]:
    corpus = ' '.join([item.title, item.snippet, ' '.join(analysis.entities), ' '.join(analysis.topics)]).lower()
    title_tokens = {token for token in market.title.lower().split() if len(token) > 3}
    category = (market.category or '').lower()

    token_hits = sum(1 for token in title_tokens if token in corpus)
    score = Decimal('0.0000')
    rationale_bits: list[str] = []
    if token_hits:
        score += Decimal(min(token_hits * 0.12, 0.6)).quantize(Decimal('0.0001'))
        rationale_bits.append(f'{token_hits} title-token matches')
    if category and category in corpus:
        score += Decimal('0.1800')
        rationale_bits.append('category match')
    score += (analysis.market_relevance_score * Decimal('0.30')).quantize(Decimal('0.0001'))
    return min(score, Decimal('1.0000')), ', '.join(rationale_bits) or 'relevance-weighted heuristic match'


def link_narratives_to_markets(*, item_ids: list[int] | None = None) -> int:
    query = NarrativeItem.objects.select_related('analysis').all()
    if item_ids:
        query = query.filter(id__in=item_ids)

    linked_count = 0
    for item in query[:100]:
        if not hasattr(item, 'analysis'):
            continue
        analysis = item.analysis
        topic_terms = [term for term in analysis.topics if term]
        entity_terms = [term for term in analysis.entities if term]
        keyword_filter = Q(title__icontains=item.title[:40])
        for term in topic_terms[:5] + entity_terms[:5]:
            keyword_filter |= Q(title__icontains=term) | Q(category__icontains=term)

        markets = Market.objects.filter(is_active=True).filter(keyword_filter).distinct()[:20]
        scored = []
        for market in markets:
            strength, rationale = _score_market_link(item=item, analysis=analysis, market=market)
            if strength < Decimal('0.2000'):
                continue
            scored.append((market, strength, rationale))

        for market, strength, rationale in sorted(scored, key=lambda row: row[1], reverse=True)[:5]:
            _, created = MarketNarrativeLink.objects.update_or_create(
                narrative_item=item,
                market=market,
                defaults={'link_strength': strength, 'rationale': rationale, 'metadata': {'heuristic': True}},
            )
            if created:
                linked_count += 1

    return linked_count

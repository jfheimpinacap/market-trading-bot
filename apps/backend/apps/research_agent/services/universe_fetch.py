from __future__ import annotations

from collections import Counter

from apps.markets.models import Market


def fetch_market_universe(*, provider_scope: list[str] | None = None, source_scope: list[str] | None = None):
    queryset = Market.objects.select_related('provider').filter(is_active=True)
    if provider_scope:
        queryset = queryset.filter(provider__slug__in=provider_scope)
    if source_scope:
        queryset = queryset.filter(source_type__in=source_scope)
    markets = list(queryset.order_by('-updated_at', '-id'))
    provider_counts = Counter(market.provider.slug for market in markets)
    return markets, dict(provider_counts)

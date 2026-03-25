from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.markets.models import Market, MarketSourceType, MarketStatus
from apps.paper_trading.services.market_pricing import get_paper_tradability
from apps.real_data_sync.services import build_sync_status
from apps.real_market_ops.services.real_scope import get_real_scope_config


TERMINAL_STATUSES = {MarketStatus.CLOSED, MarketStatus.RESOLVED, MarketStatus.CANCELLED, MarketStatus.ARCHIVED}


@dataclass
class EligibilitySnapshot:
    providers_considered: list[str]
    considered: list[Market]
    eligible: list[Market]
    excluded: list[dict]
    provider_status: dict
    scope: dict
    counters: dict


def _provider_list(scope_value: str) -> list[str]:
    if scope_value == 'kalshi':
        return ['kalshi']
    if scope_value == 'polymarket':
        return ['polymarket']
    return ['kalshi', 'polymarket']


def evaluate_real_market_eligibility(*, limit: int | None = None) -> EligibilitySnapshot:
    config = get_real_scope_config()
    sync_status = build_sync_status()
    providers = _provider_list(config.provider_scope)
    provider_view = {provider: sync_status['providers'].get(provider, {}) for provider in providers}

    max_markets = limit or config.max_real_markets_per_cycle
    queryset = Market.objects.select_related('provider').filter(
        source_type=MarketSourceType.REAL_READ_ONLY,
        is_active=True,
        status=MarketStatus.OPEN,
        provider__slug__in=providers,
    )
    queryset = queryset.order_by('-updated_at', '-id')[: max_markets * 3]

    eligible: list[Market] = []
    excluded: list[dict] = []
    skipped_stale = 0
    skipped_degraded = 0
    skipped_no_pricing = 0

    for market in queryset:
        reasons: list[str] = []
        provider_health = provider_view.get(market.provider.slug, {})
        stale = bool(provider_health.get('stale'))
        degraded = provider_health.get('availability') == 'degraded'

        if config.require_fresh_sync and config.stale_data_blocks_execution and stale:
            reasons.append('provider_stale')
            skipped_stale += 1

        if config.degraded_provider_blocks_execution and degraded:
            reasons.append('provider_degraded')
            skipped_degraded += 1

        if market.status in TERMINAL_STATUSES or market.status != MarketStatus.OPEN:
            reasons.append('market_not_open')

        if config.allowed_categories and market.category not in set(config.allowed_categories):
            reasons.append('category_not_whitelisted')
        if config.exclude_categories and market.category in set(config.exclude_categories):
            reasons.append('category_blacklisted')

        liquidity = Decimal(str(market.liquidity or 0))
        volume = Decimal(str(market.volume_24h or 0))
        if liquidity < config.min_liquidity_threshold:
            reasons.append('low_liquidity')
        if volume < config.min_volume_threshold:
            reasons.append('low_volume')

        tradability = get_paper_tradability(market)
        if not tradability.is_tradable:
            reasons.append(tradability.code.lower())
            if tradability.code == 'PRICE_UNAVAILABLE':
                skipped_no_pricing += 1

        if reasons:
            excluded.append(
                {
                    'market_id': market.id,
                    'market_title': market.title,
                    'provider': market.provider.slug,
                    'category': market.category,
                    'reasons': sorted(set(reasons)),
                }
            )
            continue

        eligible.append(market)
        if len(eligible) >= max_markets:
            break

    return EligibilitySnapshot(
        providers_considered=providers,
        considered=list(queryset),
        eligible=eligible,
        excluded=excluded,
        provider_status=provider_view,
        scope={
            'enabled': config.enabled,
            'provider_scope': config.provider_scope,
            'market_scope': config.market_scope,
            'max_real_markets_per_cycle': config.max_real_markets_per_cycle,
            'max_real_auto_trades_per_cycle': config.max_real_auto_trades_per_cycle,
            'require_fresh_sync': config.require_fresh_sync,
            'stale_data_blocks_execution': config.stale_data_blocks_execution,
            'degraded_provider_blocks_execution': config.degraded_provider_blocks_execution,
            'min_liquidity_threshold': str(config.min_liquidity_threshold),
            'min_volume_threshold': str(config.min_volume_threshold),
            'allowed_categories': config.allowed_categories,
            'exclude_categories': config.exclude_categories,
        },
        counters={
            'markets_considered': len(queryset),
            'markets_eligible': len(eligible),
            'excluded_count': len(excluded),
            'skipped_stale_count': skipped_stale,
            'skipped_degraded_provider_count': skipped_degraded,
            'skipped_no_pricing_count': skipped_no_pricing,
        },
    )

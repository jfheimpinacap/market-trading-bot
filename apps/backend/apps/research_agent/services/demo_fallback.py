from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone

from apps.markets.models import Market, MarketSourceType
from apps.paper_trading.services.market_pricing import get_paper_tradability
from apps.research_agent.services.source_fetch import ScanRawItem


@dataclass(frozen=True)
class DemoNarrativeFallbackResult:
    items: list[ScanRawItem]
    market_ids: list[int]


def is_scan_demo_fallback_enabled() -> bool:
    return bool(getattr(settings, 'SCAN_DEMO_NARRATIVE_FALLBACK_ENABLED', False))


def is_local_demo_environment() -> bool:
    environment = str(getattr(settings, 'ENVIRONMENT', '') or '').lower()
    return environment in {'local', 'test'}


def _eligible_demo_markets() -> list[Market]:
    candidates = Market.objects.filter(source_type=MarketSourceType.DEMO, is_active=True).exclude(status__in=['closed', 'resolved', 'cancelled', 'archived'])
    markets: list[Market] = []
    for market in candidates.order_by('id')[:8]:
        tradability = get_paper_tradability(market)
        if tradability.is_tradable:
            markets.append(market)
    return markets


def build_demo_narrative_fallback_items(*, market_limit: int = 3) -> DemoNarrativeFallbackResult:
    items: list[ScanRawItem] = []
    market_ids: list[int] = []
    now = timezone.now()

    for market in _eligible_demo_markets()[: max(1, market_limit)]:
        market_ids.append(market.id)
        title_anchor = (market.title.split(' ')[0] or 'market').lower()
        tag = market.ticker or market.slug or f'market-{market.id}'
        normalized_topic = f'{title_anchor} {tag} local demo narrative'.strip()
        refs = [
            ('demo_wire', 'DEMO_NARRATIVE_WIRE', 'surge'),
            ('demo_forum', 'DEMO_NARRATIVE_FORUM', 'upside'),
            ('demo_social', 'DEMO_NARRATIVE_SOCIAL', 'rise'),
        ]

        for index, (source_type, source_name, keyword) in enumerate(refs, start=1):
            title = f'{normalized_topic} {keyword}'
            items.append(
                ScanRawItem(
                    source_type=source_type,
                    source_slug=f'demo-fallback-{source_type}',
                    source_name=source_name,
                    title=title[:512],
                    url=f'https://demo.local/fallback/{market.id}/{index}',
                    raw_text=(
                        f'DEMO SYNTHETIC FALLBACK narrative for {market.title}. '
                        f'Deterministic local testing signal with conservative {keyword} framing. '
                        'This does not represent live RSS/Reddit/X data.'
                    )[:8000],
                    snippet='Demo synthetic narrative fallback signal for local V1 paper testing.'[:1000],
                    author='demo-fallback',
                    published_at=now,
                    metadata={
                        'fallback_type': 'demo_narrative',
                        'is_demo': True,
                        'is_synthetic': True,
                        'is_fallback': True,
                        'market_id': market.id,
                        'market_slug': market.slug,
                        'paper_tradable': True,
                    },
                )
            )

    return DemoNarrativeFallbackResult(items=items, market_ids=market_ids)

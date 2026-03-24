from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from provider_core.client import ReadOnlyProviderClient
from provider_core.http import get_json
from provider_core.types import NormalizedMarketRecord


class PolymarketReadOnlyClient(ReadOnlyProviderClient):
    provider_slug = 'polymarket'

    def __init__(self, base_url: str = 'https://gamma-api.polymarket.com') -> None:
        self.base_url = base_url

    def list_markets(
        self,
        *,
        limit: int = 50,
        active_only: bool = False,
        query: str | None = None,
        provider_market_id: str | None = None,
    ) -> list[NormalizedMarketRecord]:
        if provider_market_id:
            return [self.get_market(provider_market_id)]

        params: dict[str, Any] = {'limit': max(1, min(limit, 200))}
        if active_only:
            params['active'] = 'true'
        if query:
            params['query'] = query

        rows = get_json(self.base_url, '/markets', params=params)
        if isinstance(rows, dict):
            rows = rows.get('markets', [])
        return [self._normalize_market(row) for row in rows]

    def get_market(self, provider_market_id: str) -> NormalizedMarketRecord:
        row = get_json(self.base_url, f'/markets/{provider_market_id}')
        if isinstance(row, dict) and 'market' in row:
            row = row['market']
        return self._normalize_market(row)

    def _normalize_market(self, row: dict[str, Any]) -> NormalizedMarketRecord:
        probability = _to_decimal(row.get('probability') or row.get('lastTradePrice'))
        yes_price = _to_decimal(row.get('bestAsk') or row.get('lastTradePrice'))
        if yes_price is None:
            yes_price = probability

        return NormalizedMarketRecord(
            provider_name='Polymarket',
            provider_slug=self.provider_slug,
            provider_market_id=str(row.get('id') or ''),
            provider_event_id=_to_text(row.get('eventId')),
            title=_to_text(row.get('question') or row.get('title')),
            category=_to_text(row.get('category')),
            status='open' if row.get('active') else ('resolved' if row.get('closed') else 'closed'),
            url=_to_text(row.get('url')),
            is_active=bool(row.get('active')),
            market_probability=probability,
            yes_price=yes_price,
            no_price=_bounded_one_minus(yes_price),
            liquidity=_to_decimal(row.get('liquidity')),
            volume=_to_decimal(row.get('volume')),
            volume_24h=_to_decimal(row.get('volume24hr')),
            close_time=_parse_datetime(row.get('endDate') or row.get('closeTime')),
            resolution_time=_parse_datetime(row.get('resolutionDate')),
            metadata={'raw': row},
            event_title=_to_text(row.get('eventTitle')),
            event_metadata={'slug': row.get('slug')},
        )


def _to_text(value: Any) -> str:
    return str(value).strip() if value is not None else ''


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value)).quantize(Decimal('0.0001'))
    except Exception:
        return None


def _bounded_one_minus(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return max(Decimal('0.0000'), (Decimal('1.0000') - value).quantize(Decimal('0.0001')))


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None

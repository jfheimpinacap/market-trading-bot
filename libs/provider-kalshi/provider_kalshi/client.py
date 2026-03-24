from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from provider_core.client import ReadOnlyProviderClient
from provider_core.http import get_json
from provider_core.types import NormalizedMarketRecord


class KalshiReadOnlyClient(ReadOnlyProviderClient):
    provider_slug = 'kalshi'

    def __init__(self, base_url: str = 'https://api.elections.kalshi.com/trade-api/v2') -> None:
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
        if query:
            params['search'] = query
        if active_only:
            params['status'] = 'open'

        payload = get_json(self.base_url, '/markets', params=params)
        rows = payload.get('markets', [])
        return [self._normalize_market(row) for row in rows]

    def get_market(self, provider_market_id: str) -> NormalizedMarketRecord:
        payload = get_json(self.base_url, f'/markets/{provider_market_id}')
        market = payload.get('market', payload)
        return self._normalize_market(market)

    def _normalize_market(self, row: dict[str, Any]) -> NormalizedMarketRecord:
        yes_bid = _to_decimal(row.get('yes_bid'))
        yes_ask = _to_decimal(row.get('yes_ask'))
        last_price = _to_decimal(row.get('last_price'))
        yes_price = yes_ask or yes_bid or last_price
        no_price = _bounded_one_minus(yes_price)
        probability = yes_price

        return NormalizedMarketRecord(
            provider_name='Kalshi',
            provider_slug=self.provider_slug,
            provider_market_id=str(row.get('ticker') or row.get('id') or ''),
            provider_event_id=_to_text(row.get('event_ticker') or row.get('event_id')),
            title=_to_text(row.get('title')),
            category=_to_text(row.get('category')),
            status=_normalize_status(_to_text(row.get('status'))),
            url=_to_text(row.get('url') or row.get('market_url')),
            is_active=_to_text(row.get('status')).lower() == 'open',
            market_probability=probability,
            yes_price=yes_price,
            no_price=no_price,
            liquidity=_to_decimal(row.get('liquidity')),
            volume=_to_decimal(row.get('volume')),
            volume_24h=_to_decimal(row.get('volume_24h')),
            close_time=_parse_datetime(row.get('close_time') or row.get('expiration_time')),
            resolution_time=_parse_datetime(row.get('settlement_timer_seconds') and None),
            metadata={
                'raw': row,
                'orderbook': {
                    'yes_bid': yes_bid,
                    'yes_ask': yes_ask,
                },
            },
            event_title=_to_text(row.get('event_title')),
            event_metadata={'series_ticker': row.get('series_ticker')},
        )


def _to_text(value: Any) -> str:
    return str(value).strip() if value is not None else ''


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, ''):
        return None
    try:
        number = Decimal(str(value))
    except Exception:
        return None
    if number > 1:
        return (number / Decimal('100')).quantize(Decimal('0.0001'))
    return number.quantize(Decimal('0.0001'))


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
            normalized = value.replace('Z', '+00:00')
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def _normalize_status(value: str) -> str:
    known = {'open', 'closed', 'resolved', 'cancelled', 'paused', 'archived'}
    lowered = value.lower()
    return lowered if lowered in known else 'open'

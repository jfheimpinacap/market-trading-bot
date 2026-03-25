from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.markets.models import Event, EventStatus, Market, MarketSourceType, MarketStatus, MarketSnapshot, Provider
from apps.markets.provider_registry import get_provider_client


@dataclass
class IngestionResult:
    provider: str
    fetched: int = 0
    events_created: int = 0
    events_updated: int = 0
    markets_created: int = 0
    markets_updated: int = 0
    snapshots_created: int = 0
    errors: list[str] | None = None


def ingest_provider_markets(
    provider_slug: str,
    *,
    limit: int = 50,
    active_only: bool = False,
    query: str | None = None,
    provider_market_id: str | None = None,
) -> IngestionResult:
    client = get_provider_client(provider_slug)
    records = client.list_markets(
        limit=limit,
        active_only=active_only,
        query=query,
        provider_market_id=provider_market_id,
    )
    result = IngestionResult(provider=provider_slug, fetched=len(records), errors=[])
    provider = _upsert_provider(provider_slug)

    with transaction.atomic():
        for record in records:
            try:
                event, event_created = _upsert_event(provider, record)
                market, market_created = _upsert_market(provider, event, record)
                snapshot_created = _create_snapshot(market, record)

                result.events_created += int(event_created)
                result.events_updated += int(not event_created)
                result.markets_created += int(market_created)
                result.markets_updated += int(not market_created)
                result.snapshots_created += int(snapshot_created)
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f'{record.provider_market_id}: {exc}')

    return result


def _upsert_provider(provider_slug: str) -> Provider:
    names = {'kalshi': 'Kalshi (Real Read-only)', 'polymarket': 'Polymarket (Real Read-only)'}
    urls = {
        'kalshi': ('https://kalshi.com', 'https://api.elections.kalshi.com/trade-api/v2'),
        'polymarket': ('https://polymarket.com', 'https://gamma-api.polymarket.com'),
    }
    provider, _ = Provider.objects.update_or_create(
        slug=f'{provider_slug}-real',
        defaults={
            'name': names.get(provider_slug, provider_slug.title()),
            'description': 'Real market data source ingested in read-only mode.',
            'base_url': urls.get(provider_slug, ('', ''))[0],
            'api_base_url': urls.get(provider_slug, ('', ''))[1],
            'notes': 'Read-only ingestion. No trading auth, no order placement.',
            'is_active': True,
        },
    )
    return provider


def _upsert_event(provider: Provider, record):
    provider_event_id = record.provider_event_id or f"event-{slugify(record.event_title or record.title)[:100]}"
    defaults = {
        'title': record.event_title or record.title,
        'category': record.category,
        'description': 'Ingested from provider public read-only market data endpoint.',
        'status': _event_status_from_market(record.status),
        'close_time': record.close_time,
        'resolution_time': record.resolution_time,
        'metadata': record.event_metadata,
        'source_type': MarketSourceType.REAL_READ_ONLY,
    }
    return Event.objects.update_or_create(provider=provider, provider_event_id=provider_event_id, defaults=defaults)


def _upsert_market(provider: Provider, event: Event, record):
    defaults = {
        'event': event,
        'ticker': record.provider_market_id,
        'title': record.title,
        'category': record.category,
        'status': _market_status(record.status),
        'url': record.url,
        'is_active': record.is_active,
        'close_time': record.close_time,
        'resolution_time': record.resolution_time,
        'current_market_probability': record.market_probability,
        'current_yes_price': record.yes_price,
        'current_no_price': record.no_price,
        'liquidity': record.liquidity,
        'volume_24h': record.volume_24h,
        'volume_total': record.volume,
        'metadata': record.metadata,
        'resolution_source': 'Provider public read-only feed',
        'source_type': MarketSourceType.REAL_READ_ONLY,
    }
    return Market.objects.update_or_create(
        provider=provider,
        provider_market_id=record.provider_market_id,
        defaults=defaults,
    )


def _create_snapshot(market: Market, record) -> bool:
    captured_at = timezone.now().replace(microsecond=0)
    _, created = MarketSnapshot.objects.update_or_create(
        market=market,
        captured_at=captured_at,
        defaults={
            'market_probability': record.market_probability,
            'yes_price': record.yes_price,
            'no_price': record.no_price,
            'liquidity': record.liquidity,
            'volume': record.volume,
            'volume_24h': record.volume_24h,
            'metadata': {'source_type': MarketSourceType.REAL_READ_ONLY, 'provider_slug': record.provider_slug},
        },
    )
    return created


def _market_status(raw_status: str) -> str:
    known = {choice for choice, _ in MarketStatus.choices}
    return raw_status if raw_status in known else MarketStatus.OPEN


def _event_status_from_market(raw_status: str) -> str:
    if raw_status in {MarketStatus.RESOLVED, MarketStatus.CANCELLED}:
        return EventStatus.RESOLVED
    if raw_status in {MarketStatus.CLOSED, MarketStatus.ARCHIVED}:
        return EventStatus.CLOSED
    if raw_status == MarketStatus.PAUSED:
        return EventStatus.UPCOMING
    return EventStatus.OPEN

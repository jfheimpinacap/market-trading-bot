from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.markets.services.real_data_ingestion import ingest_provider_markets
from apps.real_data_sync.models import ProviderSyncRun, ProviderSyncStatus, ProviderSyncType

STALE_AFTER_MINUTES = 20
FAILURE_DEGRADED_THRESHOLD = 2


def _derive_sync_type(*, sync_type: str | None, active_only: bool, market_id: str | None) -> str:
    if market_id:
        return ProviderSyncType.SINGLE_MARKET
    if active_only:
        return ProviderSyncType.ACTIVE_ONLY
    if sync_type in {choice for choice, _ in ProviderSyncType.choices}:
        return sync_type
    return ProviderSyncType.FULL


def _status_from_error_count(error_count: int) -> str:
    if error_count <= 0:
        return ProviderSyncStatus.SUCCESS
    return ProviderSyncStatus.PARTIAL


def run_provider_sync(
    *,
    provider: str,
    sync_type: str | None = None,
    active_only: bool = False,
    limit: int = 100,
    market_id: str | None = None,
    triggered_from: str = 'api',
) -> ProviderSyncRun:
    started_at = timezone.now()
    normalized_sync_type = _derive_sync_type(sync_type=sync_type, active_only=active_only, market_id=market_id)

    run = ProviderSyncRun.objects.create(
        provider=provider,
        sync_type=normalized_sync_type,
        status=ProviderSyncStatus.RUNNING,
        started_at=started_at,
        triggered_from=triggered_from,
        details={
            'request': {
                'provider': provider,
                'sync_type': normalized_sync_type,
                'active_only': active_only,
                'limit': limit,
                'market_id': market_id,
                'triggered_from': triggered_from,
            }
        },
    )

    try:
        result = ingest_provider_markets(
            provider,
            limit=limit,
            active_only=active_only,
            provider_market_id=market_id,
        )
        error_messages = getattr(result, 'errors', [])
        run.markets_seen = result.fetched
        run.markets_created = result.markets_created
        run.markets_updated = result.markets_updated
        run.snapshots_created = result.snapshots_created
        run.errors_count = len(error_messages)
        run.status = _status_from_error_count(run.errors_count)
        run.summary = (
            f"{provider} sync {run.status}: seen={run.markets_seen}, created={run.markets_created}, "
            f"updated={run.markets_updated}, snapshots={run.snapshots_created}, errors={run.errors_count}."
        )
        run.details = {
            **run.details,
            'result': {
                'events_created': result.events_created,
                'events_updated': result.events_updated,
                'errors': error_messages,
            },
        }
    except Exception as exc:
        run.status = ProviderSyncStatus.FAILED
        run.errors_count = 1
        run.summary = f'{provider} sync FAILED: {exc}'
        run.details = {
            **run.details,
            'error': str(exc),
        }

    run.finished_at = timezone.now()
    run.save(
        update_fields=[
            'status',
            'finished_at',
            'markets_seen',
            'markets_created',
            'markets_updated',
            'snapshots_created',
            'errors_count',
            'summary',
            'details',
            'updated_at',
        ]
    )
    return run


def build_sync_status() -> dict:
    providers = ['kalshi', 'polymarket']
    now = timezone.now()
    stale_cutoff = now - timedelta(minutes=STALE_AFTER_MINUTES)
    by_provider: dict[str, dict] = {}

    for provider in providers:
        runs = ProviderSyncRun.objects.filter(provider=provider).order_by('-started_at', '-id')
        latest = runs.first()
        last_success = runs.filter(status=ProviderSyncStatus.SUCCESS).first()
        last_failed = runs.filter(status=ProviderSyncStatus.FAILED).first()

        consecutive_failures = 0
        for run in runs[:5]:
            if run.status == ProviderSyncStatus.FAILED:
                consecutive_failures += 1
            else:
                break

        is_stale = not last_success or last_success.started_at < stale_cutoff
        is_degraded = consecutive_failures >= FAILURE_DEGRADED_THRESHOLD or (latest and latest.status in {ProviderSyncStatus.FAILED, ProviderSyncStatus.PARTIAL})

        if not latest:
            availability = 'unknown'
        elif latest.status == ProviderSyncStatus.SUCCESS and not is_stale:
            availability = 'available'
        elif latest.status == ProviderSyncStatus.FAILED:
            availability = 'degraded'
        else:
            availability = 'degraded' if is_degraded or is_stale else 'available'

        by_provider[provider] = {
            'provider': provider,
            'latest_run_id': latest.id if latest else None,
            'latest_status': latest.status if latest else None,
            'latest_started_at': latest.started_at if latest else None,
            'last_success_at': last_success.started_at if last_success else None,
            'last_failed_at': last_failed.started_at if last_failed else None,
            'consecutive_failures': consecutive_failures,
            'stale': is_stale,
            'availability': availability,
            'warning': 'Provider data may be stale.' if is_stale else '',
        }

    recent_runs = ProviderSyncRun.objects.order_by('-started_at', '-id')[:20]
    return {
        'providers': by_provider,
        'recent_runs': list(recent_runs),
        'stale_after_minutes': STALE_AFTER_MINUTES,
    }

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from apps.markets.models import MarketSnapshot, MarketSourceType


@dataclass
class TimelineStep:
    timestamp: datetime
    snapshots: list[MarketSnapshot]


def build_replay_timeline(*, config: dict) -> list[TimelineStep]:
    qs = MarketSnapshot.objects.select_related('market', 'market__provider').filter(
        captured_at__gte=config['start_timestamp'],
        captured_at__lte=config['end_timestamp'],
    )

    provider_scope = str(config.get('provider_scope') or 'all')
    if provider_scope != 'all':
        providers = [item.strip() for item in provider_scope.split(',') if item.strip()]
        if providers:
            qs = qs.filter(market__provider__slug__in=providers)

    source_scope = config.get('source_scope', 'real_only')
    if source_scope == 'real_only':
        qs = qs.filter(market__source_type=MarketSourceType.REAL_READ_ONLY)
    elif source_scope == 'demo_only':
        qs = qs.filter(market__source_type=MarketSourceType.DEMO)

    if config.get('active_only', True):
        qs = qs.filter(market__is_active=True)

    snapshots = list(qs.order_by('captured_at', 'id'))
    if not snapshots:
        return []

    market_limit = int(config.get('market_limit') or 8)
    grouped: dict[datetime, list[MarketSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        grouped[snapshot.captured_at].append(snapshot)

    sampling = config.get('snapshot_sampling_interval')
    timeline: list[TimelineStep] = []
    for idx, timestamp in enumerate(sorted(grouped.keys())):
        if sampling and idx % int(sampling) != 0:
            continue
        timeline.append(TimelineStep(timestamp=timestamp, snapshots=grouped[timestamp][:market_limit]))
    return timeline

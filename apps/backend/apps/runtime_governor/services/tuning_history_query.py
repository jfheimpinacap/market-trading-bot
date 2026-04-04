from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.db.models import QuerySet
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from apps.runtime_governor.models import RuntimeTuningContextSnapshot


DEFAULT_LIMIT = 200
MAX_LIMIT = 500


@dataclass(frozen=True)
class TuningHistoryQuery:
    source_scope: str | None = None
    drift_status: str | None = None
    latest_only: bool = False
    limit: int = DEFAULT_LIMIT
    created_after: datetime | None = None
    created_before: datetime | None = None


def _parse_bool(value: str | None, *, field_name: str) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    if normalized in {'true', '1', 'yes'}:
        return True
    if normalized in {'false', '0', 'no'}:
        return False
    raise ValidationError({field_name: 'Expected true or false.'})


def _parse_limit(value: str | None) -> int:
    if value is None:
        return DEFAULT_LIMIT
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({'limit': 'Expected an integer.'}) from exc
    if parsed <= 0:
        raise ValidationError({'limit': 'Must be greater than zero.'})
    return min(parsed, MAX_LIMIT)


def _parse_datetime(value: str | None, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        raise ValidationError({field_name: 'Expected an ISO-8601 datetime string.'})
    return parsed


def parse_tuning_history_query(params, *, allow_drift_status: bool, allow_time_range: bool = False) -> TuningHistoryQuery:
    query = TuningHistoryQuery(
        source_scope=params.get('source_scope') or None,
        drift_status=params.get('drift_status') or None,
        latest_only=_parse_bool(params.get('latest_only'), field_name='latest_only'),
        limit=_parse_limit(params.get('limit')),
        created_after=_parse_datetime(params.get('created_after'), field_name='created_after') if allow_time_range else None,
        created_before=_parse_datetime(params.get('created_before'), field_name='created_before') if allow_time_range else None,
    )

    source_scope_choices = {choice for choice, _label in RuntimeTuningContextSnapshot._meta.get_field('source_scope').choices}
    if query.source_scope and query.source_scope not in source_scope_choices:
        raise ValidationError({'source_scope': f'Unknown scope: {query.source_scope}'})

    if query.drift_status:
        if not allow_drift_status:
            raise ValidationError({'drift_status': 'drift_status is not supported on this endpoint.'})
        drift_choices = {choice for choice, _label in RuntimeTuningContextSnapshot._meta.get_field('drift_status').choices}
        if query.drift_status not in drift_choices:
            raise ValidationError({'drift_status': f'Unknown drift_status: {query.drift_status}'})

    if query.created_after and query.created_before and query.created_after > query.created_before:
        raise ValidationError({'created_after': 'created_after must be before created_before.'})

    return query


def query_tuning_snapshots(query: TuningHistoryQuery) -> list[RuntimeTuningContextSnapshot]:
    queryset: QuerySet[RuntimeTuningContextSnapshot] = RuntimeTuningContextSnapshot.objects.order_by('-created_at_snapshot', '-id')
    if query.source_scope:
        queryset = queryset.filter(source_scope=query.source_scope)

    if query.latest_only:
        latest_by_scope: list[RuntimeTuningContextSnapshot] = []
        seen_scopes: set[str] = set()
        for snapshot in queryset:
            if snapshot.source_scope in seen_scopes:
                continue
            latest_by_scope.append(snapshot)
            seen_scopes.add(snapshot.source_scope)
            if len(latest_by_scope) >= query.limit:
                break
        return latest_by_scope

    return list(queryset[: query.limit])


def query_tuning_diff_snapshots(query: TuningHistoryQuery) -> list[RuntimeTuningContextSnapshot]:
    queryset: QuerySet[RuntimeTuningContextSnapshot] = RuntimeTuningContextSnapshot.objects.order_by('-created_at_snapshot', '-id')
    if query.source_scope:
        queryset = queryset.filter(source_scope=query.source_scope)
    if query.drift_status:
        queryset = queryset.filter(drift_status=query.drift_status)
    if query.created_after:
        queryset = queryset.filter(created_at_snapshot__gte=query.created_after)
    if query.created_before:
        queryset = queryset.filter(created_at_snapshot__lte=query.created_before)

    if query.latest_only:
        latest_by_scope: list[RuntimeTuningContextSnapshot] = []
        seen_scopes: set[str] = set()
        for snapshot in queryset:
            if snapshot.source_scope in seen_scopes:
                continue
            latest_by_scope.append(snapshot)
            seen_scopes.add(snapshot.source_scope)
            if len(latest_by_scope) >= query.limit:
                break
        return latest_by_scope

    return list(queryset[: query.limit])

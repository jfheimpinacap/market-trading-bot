from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.runtime_governor.models import (
    RuntimeTuningContextSnapshot,
    RuntimeTuningReviewAction,
    RuntimeTuningReviewActionType,
    RuntimeTuningReviewState,
    RuntimeTuningReviewStatus,
)


class TuningScopeSnapshotNotFound(Exception):
    pass


ATTENTION_STATUSES = {
    RuntimeTuningReviewStatus.UNREVIEWED,
    RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED,
    RuntimeTuningReviewStatus.STALE_REVIEW,
}

SUMMARY_BY_STATUS = {
    RuntimeTuningReviewStatus.UNREVIEWED: 'No manual review recorded yet',
    RuntimeTuningReviewStatus.ACKNOWLEDGED_CURRENT: 'Current tuning state acknowledged',
    RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED: 'Follow-up required for current tuning state',
    RuntimeTuningReviewStatus.STALE_REVIEW: 'Review is stale because a newer snapshot exists',
}


@dataclass(frozen=True)
class _ResolvedState:
    source_scope: str
    latest_snapshot: RuntimeTuningContextSnapshot
    state: RuntimeTuningReviewState | None
    effective_status: str
    has_newer_snapshot_than_reviewed: bool


def _runtime_deep_link(source_scope: str) -> str:
    return f'/runtime?tuningScope={source_scope}'


def _runtime_investigation_deep_link(source_scope: str) -> str:
    return f'/runtime?tuningScope={source_scope}&investigate=1'


def _latest_snapshot_by_scope() -> dict[str, RuntimeTuningContextSnapshot]:
    snapshots = RuntimeTuningContextSnapshot.objects.order_by('source_scope', '-created_at_snapshot', '-id')
    by_scope: dict[str, RuntimeTuningContextSnapshot] = {}
    for snapshot in snapshots:
        by_scope.setdefault(snapshot.source_scope, snapshot)
    return by_scope


def _get_latest_snapshot_for_scope(source_scope: str) -> RuntimeTuningContextSnapshot:
    snapshot = RuntimeTuningContextSnapshot.objects.filter(source_scope=source_scope).order_by('-created_at_snapshot', '-id').first()
    if snapshot is None:
        raise TuningScopeSnapshotNotFound(source_scope)
    return snapshot


def _resolve_effective_status(*, state: RuntimeTuningReviewState | None, latest_snapshot: RuntimeTuningContextSnapshot) -> tuple[str, bool]:
    if state is None:
        return RuntimeTuningReviewStatus.UNREVIEWED, False

    reviewed_id = state.last_reviewed_snapshot_id_value
    if reviewed_id and reviewed_id != latest_snapshot.id and state.review_status != RuntimeTuningReviewStatus.UNREVIEWED:
        return RuntimeTuningReviewStatus.STALE_REVIEW, True

    return state.review_status or RuntimeTuningReviewStatus.UNREVIEWED, False


def _build_detail_payload(resolved: _ResolvedState) -> dict[str, object]:
    state = resolved.state
    stored_status = state.review_status if state else RuntimeTuningReviewStatus.UNREVIEWED
    last_reviewed_snapshot_id = state.last_reviewed_snapshot_id_value if state else None
    return {
        'source_scope': resolved.source_scope,
        'effective_review_status': resolved.effective_status,
        'stored_review_status': stored_status,
        'latest_snapshot_id': resolved.latest_snapshot.id,
        'last_reviewed_snapshot_id': last_reviewed_snapshot_id,
        'has_newer_snapshot_than_reviewed': resolved.has_newer_snapshot_than_reviewed,
        'last_action_type': state.last_action_type if state else '',
        'last_action_at': state.last_action_at if state else None,
        'review_summary': SUMMARY_BY_STATUS[resolved.effective_status],
        'runtime_deep_link': _runtime_deep_link(resolved.source_scope),
        'runtime_investigation_deep_link': _runtime_investigation_deep_link(resolved.source_scope),
    }


def _resolve_scope_state(source_scope: str) -> _ResolvedState:
    latest = _get_latest_snapshot_for_scope(source_scope)
    state = RuntimeTuningReviewState.objects.filter(source_scope=source_scope).first()
    effective_status, has_newer = _resolve_effective_status(state=state, latest_snapshot=latest)
    return _ResolvedState(
        source_scope=source_scope,
        latest_snapshot=latest,
        state=state,
        effective_status=effective_status,
        has_newer_snapshot_than_reviewed=has_newer,
    )


def get_tuning_review_state_detail(*, source_scope: str) -> dict[str, object]:
    return _build_detail_payload(_resolve_scope_state(source_scope))


def list_tuning_review_states(
    *,
    source_scope: str | None = None,
    effective_status: str | None = None,
    needs_attention: bool | None = None,
) -> list[dict[str, object]]:
    latest_by_scope = _latest_snapshot_by_scope()
    if source_scope:
        latest = latest_by_scope.get(source_scope)
        if latest is None:
            return []
        latest_by_scope = {source_scope: latest}

    states_by_scope = {
        state.source_scope: state
        for state in RuntimeTuningReviewState.objects.filter(source_scope__in=list(latest_by_scope.keys()))
    }

    rows: list[dict[str, object]] = []
    for scope, latest in latest_by_scope.items():
        state = states_by_scope.get(scope)
        status_value, has_newer = _resolve_effective_status(state=state, latest_snapshot=latest)
        row = _build_detail_payload(
            _ResolvedState(
                source_scope=scope,
                latest_snapshot=latest,
                state=state,
                effective_status=status_value,
                has_newer_snapshot_than_reviewed=has_newer,
            )
        )
        rows.append(row)

    if effective_status:
        rows = [row for row in rows if row['effective_review_status'] == effective_status]
    if needs_attention is True:
        rows = [row for row in rows if row['effective_review_status'] in ATTENTION_STATUSES]
    if needs_attention is False:
        rows = [row for row in rows if row['effective_review_status'] not in ATTENTION_STATUSES]

    return sorted(rows, key=lambda row: str(row['source_scope']))


def _record_action(*, source_scope: str, action_type: str, snapshot: RuntimeTuningContextSnapshot, resulting_status: str) -> None:
    RuntimeTuningReviewAction.objects.create(
        source_scope=source_scope,
        action_type=action_type,
        snapshot=snapshot,
        snapshot_id_value=snapshot.id,
        resulting_review_status=resulting_status,
    )


def acknowledge_current_scope(*, source_scope: str) -> dict[str, object]:
    latest_snapshot = _get_latest_snapshot_for_scope(source_scope)
    state, _ = RuntimeTuningReviewState.objects.get_or_create(source_scope=source_scope)
    state.last_reviewed_snapshot = latest_snapshot
    state.last_reviewed_snapshot_id_value = latest_snapshot.id
    state.review_status = RuntimeTuningReviewStatus.ACKNOWLEDGED_CURRENT
    state.last_action_type = RuntimeTuningReviewActionType.ACKNOWLEDGE_CURRENT
    state.last_action_at = timezone.now()
    state.save(update_fields=[
        'last_reviewed_snapshot',
        'last_reviewed_snapshot_id_value',
        'review_status',
        'last_action_type',
        'last_action_at',
        'updated_at',
    ])
    _record_action(
        source_scope=source_scope,
        action_type=RuntimeTuningReviewActionType.ACKNOWLEDGE_CURRENT,
        snapshot=latest_snapshot,
        resulting_status=RuntimeTuningReviewStatus.ACKNOWLEDGED_CURRENT,
    )
    return get_tuning_review_state_detail(source_scope=source_scope)


def mark_followup_required(*, source_scope: str) -> dict[str, object]:
    latest_snapshot = _get_latest_snapshot_for_scope(source_scope)
    state, _ = RuntimeTuningReviewState.objects.get_or_create(source_scope=source_scope)
    state.last_reviewed_snapshot = latest_snapshot
    state.last_reviewed_snapshot_id_value = latest_snapshot.id
    state.review_status = RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED
    state.last_action_type = RuntimeTuningReviewActionType.MARK_FOLLOWUP_REQUIRED
    state.last_action_at = timezone.now()
    state.save(update_fields=[
        'last_reviewed_snapshot',
        'last_reviewed_snapshot_id_value',
        'review_status',
        'last_action_type',
        'last_action_at',
        'updated_at',
    ])
    _record_action(
        source_scope=source_scope,
        action_type=RuntimeTuningReviewActionType.MARK_FOLLOWUP_REQUIRED,
        snapshot=latest_snapshot,
        resulting_status=RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED,
    )
    return get_tuning_review_state_detail(source_scope=source_scope)


def clear_review_state(*, source_scope: str) -> dict[str, object]:
    latest_snapshot = _get_latest_snapshot_for_scope(source_scope)
    now = timezone.now()
    RuntimeTuningReviewState.objects.filter(source_scope=source_scope).delete()
    _record_action(
        source_scope=source_scope,
        action_type=RuntimeTuningReviewActionType.CLEAR_REVIEW_STATE,
        snapshot=latest_snapshot,
        resulting_status=RuntimeTuningReviewStatus.UNREVIEWED,
    )
    return {
        'source_scope': source_scope,
        'effective_review_status': RuntimeTuningReviewStatus.UNREVIEWED,
        'stored_review_status': RuntimeTuningReviewStatus.UNREVIEWED,
        'latest_snapshot_id': latest_snapshot.id,
        'last_reviewed_snapshot_id': None,
        'has_newer_snapshot_than_reviewed': False,
        'last_action_type': RuntimeTuningReviewActionType.CLEAR_REVIEW_STATE,
        'last_action_at': now,
        'review_summary': SUMMARY_BY_STATUS[RuntimeTuningReviewStatus.UNREVIEWED],
        'runtime_deep_link': _runtime_deep_link(source_scope),
        'runtime_investigation_deep_link': _runtime_investigation_deep_link(source_scope),
    }


def list_tuning_review_actions(*, source_scope: str | None = None, limit: int | None = None):
    queryset = RuntimeTuningReviewAction.objects.all()
    if source_scope:
        queryset = queryset.filter(source_scope=source_scope)
    queryset = queryset.order_by('-created_at', '-id')
    if limit is not None:
        queryset = queryset[: max(limit, 0)]
    return queryset

from __future__ import annotations

from apps.runtime_governor.models import (
    RuntimeTuningReviewAction,
    RuntimeTuningReviewActionType,
    RuntimeTuningReviewStatus,
)
from apps.runtime_governor.services.tuning_review_state import (
    TuningScopeSnapshotNotFound,
    get_tuning_review_state_detail,
)

DEFAULT_ACTIVITY_LIMIT = 10

_LABEL_BY_ACTION = {
    RuntimeTuningReviewActionType.ACKNOWLEDGE_CURRENT: 'ACKNOWLEDGED',
    RuntimeTuningReviewActionType.MARK_FOLLOWUP_REQUIRED: 'FOLLOWUP_MARKED',
    RuntimeTuningReviewActionType.CLEAR_REVIEW_STATE: 'REVIEW_CLEARED',
}

_ACTION_REASON_CODES = {
    RuntimeTuningReviewActionType.ACKNOWLEDGE_CURRENT: 'ACTION_ACKNOWLEDGE_CURRENT',
    RuntimeTuningReviewActionType.MARK_FOLLOWUP_REQUIRED: 'ACTION_MARK_FOLLOWUP_REQUIRED',
    RuntimeTuningReviewActionType.CLEAR_REVIEW_STATE: 'ACTION_CLEAR_REVIEW_STATE',
}

_STATE_REASON_CODES = {
    RuntimeTuningReviewStatus.ACKNOWLEDGED_CURRENT: 'STATE_NOW_ACKNOWLEDGED',
    RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED: 'STATE_NOW_FOLLOWUP',
    RuntimeTuningReviewStatus.UNREVIEWED: 'STATE_NOW_UNREVIEWED',
}


def _runtime_investigation_deep_link(source_scope: str) -> str:
    return f'/runtime?tuningScope={source_scope}&investigate=1'


def _serialize_action_item(action: RuntimeTuningReviewAction) -> dict[str, object]:
    scope_state = get_tuning_review_state_detail(source_scope=action.source_scope)
    reason_codes = [_ACTION_REASON_CODES[action.action_type]]
    state_reason = _STATE_REASON_CODES.get(action.resulting_review_status)
    if state_reason:
        reason_codes.append(state_reason)
    return {
        'source_scope': action.source_scope,
        'action_type': action.action_type,
        'created_at': action.created_at,
        'resulting_review_status': action.resulting_review_status,
        'snapshot_id': action.snapshot_id_value,
        'activity_label': _LABEL_BY_ACTION[action.action_type],
        'activity_reason_codes': reason_codes,
        'scope_review_summary': scope_state['review_summary'],
        'runtime_investigation_deep_link': _runtime_investigation_deep_link(action.source_scope),
        'effective_review_status': scope_state['effective_review_status'],
        'has_newer_snapshot_than_reviewed': scope_state['has_newer_snapshot_than_reviewed'],
    }


def _build_queryset(*, source_scope: str | None = None, action_type: str | None = None):
    queryset = RuntimeTuningReviewAction.objects.all()
    if source_scope:
        queryset = queryset.filter(source_scope=source_scope)
    if action_type:
        queryset = queryset.filter(action_type=action_type)
    return queryset.order_by('-created_at', '-id')


def build_tuning_review_activity(
    *,
    source_scope: str | None = None,
    action_type: str | None = None,
    limit: int = DEFAULT_ACTIVITY_LIMIT,
) -> dict[str, object]:
    queryset = _build_queryset(source_scope=source_scope, action_type=action_type)
    rows = list(queryset[: max(limit, 0)])
    items = [_serialize_action_item(row) for row in rows]
    latest = items[0] if items else None
    summary = f'{len(items)} runtime tuning review actions recorded recently'
    if latest:
        summary = (
            f'{len(items)} runtime tuning review actions recorded recently. '
            f"Most recent action was {latest['activity_label']} on {latest['source_scope']}"
        )
    return {
        'activity_count': len(items),
        'latest_action_at': latest['created_at'] if latest else None,
        'activity_summary': summary,
        'items': items,
    }


def get_tuning_review_activity_detail(*, source_scope: str) -> dict[str, object]:
    queryset = _build_queryset(source_scope=source_scope)
    rows = list(queryset)
    if not rows:
        raise TuningScopeSnapshotNotFound(source_scope)
    items = [_serialize_action_item(row) for row in rows]
    return {
        'source_scope': source_scope,
        'activity_count': len(items),
        'latest_action_at': items[0]['created_at'],
        'scope_activity_summary': f'{len(items)} review actions recorded for {source_scope}',
        'items': items,
    }

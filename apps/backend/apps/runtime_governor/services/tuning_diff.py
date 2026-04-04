from __future__ import annotations

from typing import Any

from django.db.models import Q

from apps.runtime_governor.models import RuntimeTuningContextSnapshot


def _normalize_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _diff_dict(*, previous: dict[str, Any], current: dict[str, Any], namespace: str) -> tuple[dict[str, Any], dict[str, Any]]:
    changed: dict[str, Any] = {}
    unchanged: dict[str, Any] = {}
    for key in sorted(set(previous) | set(current)):
        previous_value = previous.get(key)
        current_value = current.get(key)
        target_key = f'{namespace}.{key}'
        if previous_value != current_value:
            changed[target_key] = {
                'previous': previous_value,
                'current': current_value,
            }
        else:
            unchanged[target_key] = current_value
    return changed, unchanged


def _build_summary(*, drift_status: str, changed_fields: dict[str, Any]) -> str:
    if not changed_fields:
        return f'{drift_status}: no field-level changes vs previous snapshot.'
    changed_field_names = sorted(changed_fields.keys())
    if len(changed_field_names) <= 4:
        joined = ', '.join(changed_field_names)
        return f'{drift_status}: changed {len(changed_field_names)} field(s): {joined}.'
    preview = ', '.join(changed_field_names[:4])
    return f'{drift_status}: changed {len(changed_field_names)} field(s): {preview}, and {len(changed_field_names) - 4} more.'


def build_tuning_context_diff(
    *,
    snapshot: RuntimeTuningContextSnapshot,
    previous: RuntimeTuningContextSnapshot | None,
) -> dict[str, Any]:
    changed_fields: dict[str, Any] = {}
    unchanged_fields: dict[str, Any] = {}

    base_fields = (
        'tuning_profile_name',
        'tuning_profile_fingerprint',
    )
    for field_name in base_fields:
        previous_value = getattr(previous, field_name) if previous else None
        current_value = getattr(snapshot, field_name)
        if previous is None or previous_value != current_value:
            changed_fields[field_name] = {'previous': previous_value, 'current': current_value}
        else:
            unchanged_fields[field_name] = current_value

    previous_effective_values = _normalize_object(previous.effective_values if previous else {})
    current_effective_values = _normalize_object(snapshot.effective_values)
    effective_changed, effective_unchanged = _diff_dict(
        previous=previous_effective_values,
        current=current_effective_values,
        namespace='effective_values',
    )
    changed_fields.update(effective_changed)
    unchanged_fields.update(effective_unchanged)

    previous_guardrails = _normalize_object(previous_effective_values.get('tuning_guardrail_summary') if previous else {})
    current_guardrails = _normalize_object(current_effective_values.get('tuning_guardrail_summary'))
    if previous_guardrails or current_guardrails:
        guardrails_changed, guardrails_unchanged = _diff_dict(
            previous=previous_guardrails,
            current=current_guardrails,
            namespace='guardrails',
        )
        changed_fields.update(guardrails_changed)
        unchanged_fields.update(guardrails_unchanged)

    return {
        'source_scope': snapshot.source_scope,
        'current_snapshot_id': snapshot.id,
        'previous_snapshot_id': previous.id if previous else None,
        'drift_status': snapshot.drift_status,
        'changed_fields': changed_fields,
        'unchanged_fields': unchanged_fields,
        'diff_summary': _build_summary(drift_status=snapshot.drift_status, changed_fields=changed_fields),
        'created_at': snapshot.created_at_snapshot,
    }


def build_tuning_context_diffs(*, snapshot_id: int | None = None) -> list[dict[str, Any]]:
    queryset = RuntimeTuningContextSnapshot.objects.order_by('-created_at_snapshot', '-id')
    if snapshot_id is not None:
        queryset = queryset.filter(id=snapshot_id)

    snapshots = list(queryset[:200])
    diffs: list[dict[str, Any]] = []
    for snapshot in snapshots:
        previous = (
            RuntimeTuningContextSnapshot.objects.filter(source_scope=snapshot.source_scope)
            .filter(
                Q(created_at_snapshot__lt=snapshot.created_at_snapshot)
                | Q(created_at_snapshot=snapshot.created_at_snapshot, id__lt=snapshot.id)
            )
            .order_by('-created_at_snapshot', '-id')
            .first()
        )
        diffs.append(build_tuning_context_diff(snapshot=snapshot, previous=previous))
    return diffs

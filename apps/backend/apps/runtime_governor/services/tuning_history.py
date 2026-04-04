from __future__ import annotations

from typing import Any

from apps.runtime_governor.models import (
    RuntimeTuningContextDriftStatus,
    RuntimeTuningContextSnapshot,
)
from apps.runtime_governor.services.tuning_context import build_runtime_tuning_context

SUMMARY_SCOPE_BY_SOURCE_SCOPE = {
    'runtime_feedback': 'runtime_feedback_summary',
    'operating_mode': 'operating_mode_summary',
    'mode_stabilization': 'mode_stabilization_summary',
    'mode_enforcement': 'mode_enforcement_summary',
}


def _derive_drift(*, previous: RuntimeTuningContextSnapshot | None, profile_name: str, fingerprint: str) -> tuple[str, str]:
    if previous is None:
        return RuntimeTuningContextDriftStatus.INITIAL, 'First snapshot for this scope.'
    if previous.tuning_profile_fingerprint == fingerprint:
        return RuntimeTuningContextDriftStatus.NO_CHANGE, 'Fingerprint unchanged vs previous snapshot.'
    if previous.tuning_profile_name == profile_name:
        return RuntimeTuningContextDriftStatus.MINOR_CONTEXT_CHANGE, 'Fingerprint changed with same profile name.'
    return RuntimeTuningContextDriftStatus.PROFILE_CHANGE, 'Profile name changed vs previous snapshot.'


def create_tuning_context_snapshot(
    *,
    source_scope: str,
    source_run_id: int | None = None,
    tuning_context: dict[str, Any] | None = None,
) -> RuntimeTuningContextSnapshot:
    summary_scope = SUMMARY_SCOPE_BY_SOURCE_SCOPE[source_scope]
    context = tuning_context or build_runtime_tuning_context(summary_scope=summary_scope)
    previous = RuntimeTuningContextSnapshot.objects.filter(source_scope=source_scope).order_by('-created_at_snapshot', '-id').first()
    drift_status, drift_summary = _derive_drift(
        previous=previous,
        profile_name=str(context.get('tuning_profile_name', '')),
        fingerprint=str(context.get('tuning_profile_fingerprint', '')),
    )
    return RuntimeTuningContextSnapshot.objects.create(
        source_scope=source_scope,
        source_run_id=source_run_id,
        tuning_profile_name=str(context.get('tuning_profile_name', '')),
        tuning_profile_fingerprint=str(context.get('tuning_profile_fingerprint', '')),
        tuning_profile_summary=str(context.get('tuning_profile_summary', ''))[:255],
        effective_values=context.get('tuning_effective_values') or {},
        drift_status=drift_status,
        drift_summary=drift_summary,
    )


def build_tuning_context_drift_summary() -> dict[str, Any]:
    latest_by_scope: dict[str, Any] = {}
    for source_scope in SUMMARY_SCOPE_BY_SOURCE_SCOPE:
        latest = RuntimeTuningContextSnapshot.objects.filter(source_scope=source_scope).order_by('-created_at_snapshot', '-id').first()
        latest_by_scope[source_scope] = {
            'latest_snapshot_id': latest.id if latest else None,
            'source_run_id': latest.source_run_id if latest else None,
            'tuning_profile_name': latest.tuning_profile_name if latest else None,
            'tuning_profile_fingerprint': latest.tuning_profile_fingerprint if latest else None,
            'drift_status': latest.drift_status if latest else None,
            'drift_summary': latest.drift_summary if latest else None,
            'created_at': latest.created_at_snapshot if latest else None,
        }
    return {
        'total_snapshots': RuntimeTuningContextSnapshot.objects.count(),
        'status_counts': {
            RuntimeTuningContextDriftStatus.INITIAL: RuntimeTuningContextSnapshot.objects.filter(
                drift_status=RuntimeTuningContextDriftStatus.INITIAL
            ).count(),
            RuntimeTuningContextDriftStatus.NO_CHANGE: RuntimeTuningContextSnapshot.objects.filter(
                drift_status=RuntimeTuningContextDriftStatus.NO_CHANGE
            ).count(),
            RuntimeTuningContextDriftStatus.MINOR_CONTEXT_CHANGE: RuntimeTuningContextSnapshot.objects.filter(
                drift_status=RuntimeTuningContextDriftStatus.MINOR_CONTEXT_CHANGE
            ).count(),
            RuntimeTuningContextDriftStatus.PROFILE_CHANGE: RuntimeTuningContextSnapshot.objects.filter(
                drift_status=RuntimeTuningContextDriftStatus.PROFILE_CHANGE
            ).count(),
        },
        'latest_by_scope': latest_by_scope,
    }

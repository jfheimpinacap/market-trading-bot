from __future__ import annotations

from collections import defaultdict

from apps.runtime_governor.models import RuntimeTuningContextSnapshot
from apps.runtime_governor.services.tuning_correlation import RUN_MODEL_BY_SCOPE
from apps.runtime_governor.services.tuning_links import build_latest_diff_links


def _build_digest_summary(*, snapshot: RuntimeTuningContextSnapshot, run_started_at) -> str:
    run_label = f"run #{snapshot.source_run_id}" if snapshot.source_run_id else 'run n/a'
    run_time_label = f" ({run_started_at.isoformat()})" if run_started_at else ''
    return (
        f"Scope {snapshot.source_scope}: latest tuning snapshot #{snapshot.id} uses profile "
        f"{snapshot.tuning_profile_name} ({snapshot.tuning_profile_fingerprint}) with drift "
        f"{snapshot.drift_status}; correlated {run_label}{run_time_label}."
    )


def build_tuning_scope_digest(*, source_scope: str | None = None) -> list[dict]:
    snapshots_qs = RuntimeTuningContextSnapshot.objects.all()
    if source_scope:
        snapshots_qs = snapshots_qs.filter(source_scope=source_scope)

    latest_by_scope: dict[str, RuntimeTuningContextSnapshot] = {}
    for snapshot in snapshots_qs.order_by('-created_at_snapshot', '-id'):
        if snapshot.source_scope not in latest_by_scope:
            latest_by_scope[snapshot.source_scope] = snapshot

    run_ids_by_scope: dict[str, set[int]] = defaultdict(set)
    for snapshot in latest_by_scope.values():
        if snapshot.source_run_id:
            run_ids_by_scope[snapshot.source_scope].add(snapshot.source_run_id)

    run_started_at_by_scope: dict[str, dict[int, object]] = {}
    for scope, run_ids in run_ids_by_scope.items():
        model = RUN_MODEL_BY_SCOPE.get(scope)
        if not model:
            continue
        run_started_at_by_scope[scope] = {run.id: run.started_at for run in model.objects.filter(id__in=run_ids)}

    latest_diff_links_by_scope = build_latest_diff_links(latest_snapshots=list(latest_by_scope.values()))

    digests = []
    for scope in sorted(latest_by_scope.keys()):
        snapshot = latest_by_scope[scope]
        run_started_at = run_started_at_by_scope.get(scope, {}).get(snapshot.source_run_id)
        latest_diff = latest_diff_links_by_scope.get(
            scope,
            {
                'latest_diff_snapshot_id': None,
                'latest_diff_status': None,
                'latest_diff_summary': None,
            },
        )
        digests.append(
            {
                'source_scope': scope,
                'latest_snapshot_id': snapshot.id,
                'latest_run_id': snapshot.source_run_id,
                'tuning_profile_name': snapshot.tuning_profile_name,
                'tuning_profile_fingerprint': snapshot.tuning_profile_fingerprint,
                'latest_drift_status': snapshot.drift_status,
                'latest_snapshot_created_at': snapshot.created_at_snapshot,
                'digest_summary': _build_digest_summary(snapshot=snapshot, run_started_at=run_started_at),
                'latest_diff_snapshot_id': latest_diff['latest_diff_snapshot_id'],
                'latest_diff_status': latest_diff['latest_diff_status'],
                'latest_diff_summary': latest_diff['latest_diff_summary'],
            }
        )
    return digests

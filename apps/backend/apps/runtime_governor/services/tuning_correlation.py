from __future__ import annotations

from collections import defaultdict

from apps.runtime_governor.models import (
    GlobalModeEnforcementRun,
    GlobalRuntimePostureRun,
    RuntimeFeedbackRun,
    RuntimeModeStabilizationRun,
    RuntimeTuningContextSnapshot,
)


RUN_MODEL_BY_SCOPE = {
    'runtime_feedback': RuntimeFeedbackRun,
    'operating_mode': GlobalRuntimePostureRun,
    'mode_stabilization': RuntimeModeStabilizationRun,
    'mode_enforcement': GlobalModeEnforcementRun,
}


def _build_summary(snapshot: RuntimeTuningContextSnapshot) -> str:
    return (
        f"Scope {snapshot.source_scope} run #{snapshot.source_run_id or 'n/a'} linked to "
        f"tuning snapshot #{snapshot.id} using profile {snapshot.tuning_profile_name} "
        f"({snapshot.tuning_profile_fingerprint}) with drift {snapshot.drift_status}."
    )


def build_tuning_run_correlations(*, snapshots: list[RuntimeTuningContextSnapshot]) -> list[dict]:
    run_ids_by_scope: dict[str, set[int]] = defaultdict(set)
    for snapshot in snapshots:
        if snapshot.source_run_id:
            run_ids_by_scope[snapshot.source_scope].add(snapshot.source_run_id)

    run_started_at_by_scope: dict[str, dict[int, object]] = {}
    for scope, run_ids in run_ids_by_scope.items():
        model = RUN_MODEL_BY_SCOPE.get(scope)
        if not model:
            continue
        run_started_at_by_scope[scope] = {run.id: run.started_at for run in model.objects.filter(id__in=run_ids)}

    return [
        {
            'source_scope': snapshot.source_scope,
            'source_run_id': snapshot.source_run_id,
            'tuning_snapshot_id': snapshot.id,
            'tuning_profile_name': snapshot.tuning_profile_name,
            'tuning_profile_fingerprint': snapshot.tuning_profile_fingerprint,
            'drift_status': snapshot.drift_status,
            'run_created_at': run_started_at_by_scope.get(snapshot.source_scope, {}).get(snapshot.source_run_id),
            'correlation_summary': _build_summary(snapshot),
        }
        for snapshot in snapshots
    ]

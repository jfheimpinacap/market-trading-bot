from __future__ import annotations

from apps.incident_commander.models import IncidentRecoveryRun, RecoveryRunStatus
from apps.memory_retrieval.services import run_indexing
from apps.operator_alerts.services import rebuild_operator_alerts


def run_recovery_for_incident(*, incident) -> IncidentRecoveryRun:
    run = IncidentRecoveryRun.objects.create(
        incident=incident,
        run_status=RecoveryRunStatus.STARTED,
        trigger='incident_commander',
        summary='Recovery started.',
        metadata={'incident_type': incident.incident_type},
    )

    try:
        if incident.incident_type == 'memory_index_failure':
            result = run_indexing(force_reembed=False)
            run.run_status = RecoveryRunStatus.SUCCESS
            run.summary = 'Memory indexing retry completed.'
            run.metadata = {**(run.metadata or {}), 'result': result}
        elif incident.incident_type == 'alerts_delivery_failure':
            result = rebuild_operator_alerts()
            run.run_status = RecoveryRunStatus.SUCCESS
            run.summary = 'Alert aggregation rebuild completed.'
            run.metadata = {**(run.metadata or {}), 'result': result}
        else:
            run.run_status = RecoveryRunStatus.SKIPPED
            run.summary = 'No safe automatic recovery step configured for this incident type.'
    except Exception as exc:  # pragma: no cover - defensive
        run.run_status = RecoveryRunStatus.FAILED
        run.summary = f'Recovery failed: {exc}'

    run.save()
    return run

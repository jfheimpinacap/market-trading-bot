from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.incident_commander.models import DegradedModeState, IncidentRecord
from apps.incident_commander.services import mitigate_incident, run_detection
from apps.operator_alerts.models import OperatorAlert
from apps.operator_queue.models import OperatorQueueItem
from apps.rollout_manager.models import StackRolloutRun

from apps.chaos_lab.models import ChaosObservation, ObservationSeverity


@dataclass
class ObservationResult:
    incident_ids: list[int]
    observation_ids: list[int]


def _obs(*, run, code: str, message: str, severity: str = ObservationSeverity.INFO, details: dict | None = None) -> int:
    obs = ChaosObservation.objects.create(
        run=run,
        code=code,
        message=message,
        severity=severity,
        observed_at=timezone.now(),
        details=details or {},
    )
    return obs.id


def collect_observations(*, run, started_at, incident_before_ids: set[int], alert_before: int, queue_before: int, rollout_before_rollback_count: int) -> ObservationResult:
    observation_ids: list[int] = []

    detection_result = run_detection()
    incident_ids = detection_result.get('incident_ids', [])
    observation_ids.append(_obs(run=run, code='detection_run', message=f"Incident detection completed; detected_count={detection_result.get('detected_count', 0)}.", details=detection_result))

    new_incidents = list(IncidentRecord.objects.filter(id__in=incident_ids).exclude(id__in=incident_before_ids))
    if not new_incidents:
        observation_ids.append(_obs(run=run, code='no_incident_created', severity=ObservationSeverity.WARNING, message='No new incident created for this chaos run. This can be valid when dedupe matched existing signals.'))

    for incident in new_incidents:
        delay = (incident.first_seen_at - started_at).total_seconds()
        observation_ids.append(_obs(run=run, code='incident_created', message=f'Incident #{incident.id} created ({incident.incident_type}).', details={'incident_id': incident.id, 'incident_type': incident.incident_type, 'detection_delay_seconds': max(delay, 0)}))
        mitigated = mitigate_incident(incident=incident)
        observation_ids.append(_obs(run=run, code='incident_mitigated', message=f'Incident #{incident.id} mitigation applied; status={mitigated.status}.', details={'incident_id': incident.id, 'status': mitigated.status}))

    degraded = DegradedModeState.objects.order_by('-updated_at', '-id').first()
    if degraded and degraded.state != 'normal':
        observation_ids.append(_obs(run=run, code='degraded_mode_entered', severity=ObservationSeverity.WARNING, message=f'Degraded mode entered: {degraded.state}.', details={'state': degraded.state, 'mission_control_paused': degraded.mission_control_paused, 'rollout_enabled': degraded.rollout_enabled}))

    alerts_delta = OperatorAlert.objects.count() - alert_before
    queue_delta = OperatorQueueItem.objects.count() - queue_before
    rollback_count = StackRolloutRun.objects.filter(status='ROLLED_BACK').count() - rollout_before_rollback_count

    if alerts_delta > 0:
        observation_ids.append(_obs(run=run, code='alert_emitted', message=f'Alerts emitted during run: {alerts_delta}.', details={'alerts_created': alerts_delta}))
    if queue_delta > 0:
        observation_ids.append(_obs(run=run, code='queue_item_created', message=f'Operator queue items created during run: {queue_delta}.', details={'queue_items_created': queue_delta}))
    if rollback_count > 0:
        observation_ids.append(_obs(run=run, code='rollback_triggered', severity=ObservationSeverity.WARNING, message='Rollout rollback triggered by mitigation policy.', details={'rollback_count': rollback_count}))

    return ObservationResult(incident_ids=[item.id for item in new_incidents], observation_ids=observation_ids)

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.execution_simulator.models import PaperExecutionAttempt
from apps.incident_commander.models import IncidentRecord, IncidentSeverity, IncidentStatus, IncidentType
from apps.llm_local.services import build_llm_status
from apps.memory_retrieval.models import MemoryDocument
from apps.mission_control.models import MissionControlCycle
from apps.notification_center.models import NotificationDelivery, NotificationDeliveryStatus
from apps.operator_queue.models import OperatorQueueItem, OperatorQueueStatus
from apps.real_data_sync.models import ProviderSyncRun, ProviderSyncStatus
from apps.rollout_manager.models import RolloutGuardrailEvent
from apps.runtime_governor.services import get_runtime_state
from apps.safety_guard.services import get_safety_status


def _upsert_incident(*, dedupe_key: str, incident_type: str, severity: str, title: str, summary: str, source_app: str, related_object_type: str | None = None, related_object_id: str | None = None, metadata: dict | None = None) -> IncidentRecord:
    now = timezone.now()
    existing = IncidentRecord.objects.filter(dedupe_key=dedupe_key).exclude(status=IncidentStatus.RESOLVED).first()
    if existing:
        existing.last_seen_at = now
        existing.summary = summary
        existing.severity = severity
        existing.metadata = {**(existing.metadata or {}), **(metadata or {})}
        existing.save(update_fields=['last_seen_at', 'summary', 'severity', 'metadata', 'updated_at'])
        return existing

    return IncidentRecord.objects.create(
        incident_type=incident_type,
        severity=severity,
        status=IncidentStatus.OPEN,
        title=title,
        summary=summary,
        source_app=source_app,
        related_object_type=related_object_type,
        related_object_id=related_object_id,
        first_seen_at=now,
        last_seen_at=now,
        dedupe_key=dedupe_key,
        metadata=metadata or {},
    )


def run_detection() -> dict:
    detected_ids: list[int] = []
    now = timezone.now()

    stale_cutoff = now - timedelta(hours=2)
    latest_sync = ProviderSyncRun.objects.order_by('-started_at', '-id').first()
    if latest_sync and (latest_sync.started_at < stale_cutoff or latest_sync.status in {ProviderSyncStatus.FAILED, ProviderSyncStatus.PARTIAL}):
        incident = _upsert_incident(
            dedupe_key='stale-data:provider-sync',
            incident_type=IncidentType.STALE_DATA,
            severity=IncidentSeverity.HIGH,
            title='Provider sync stale/degraded',
            summary=f'Latest provider sync run is {latest_sync.status} and started at {latest_sync.started_at.isoformat()}.',
            source_app='real_data_sync',
            related_object_type='provider_sync_run',
            related_object_id=str(latest_sync.id),
            metadata={'status': latest_sync.status, 'errors_count': latest_sync.errors_count},
        )
        detected_ids.append(incident.id)

    recent_cycles = list(MissionControlCycle.objects.order_by('-started_at', '-id')[:5])
    failed_cycles = [cycle for cycle in recent_cycles if cycle.status == 'FAILED']
    if len(failed_cycles) >= 3:
        incident = _upsert_incident(
            dedupe_key='mission-control:repeated-failures',
            incident_type=IncidentType.MISSION_CONTROL_FAILURE,
            severity=IncidentSeverity.CRITICAL,
            title='Mission control repeated cycle failures',
            summary=f'{len(failed_cycles)} of last {len(recent_cycles)} cycles failed.',
            source_app='mission_control',
            metadata={'failed_cycle_ids': [item.id for item in failed_cycles]},
        )
        detected_ids.append(incident.id)

    critical_event = RolloutGuardrailEvent.objects.filter(severity__iexact='CRITICAL').order_by('-created_at', '-id').first()
    if critical_event:
        incident = _upsert_incident(
            dedupe_key=f'rollout-guardrail:{critical_event.run_id}',
            incident_type=IncidentType.ROLLOUT_GUARDRAIL,
            severity=IncidentSeverity.CRITICAL,
            title='Rollout guardrail triggered critical rollback risk',
            summary=critical_event.reason or f'Critical guardrail {critical_event.code} fired for run {critical_event.run_id}.',
            source_app='rollout_manager',
            related_object_type='stack_rollout_run',
            related_object_id=str(critical_event.run_id),
            metadata={'guardrail_code': critical_event.code},
        )
        detected_ids.append(incident.id)

    recent_attempts = list(PaperExecutionAttempt.objects.order_by('-created_at', '-id')[:25])
    if recent_attempts:
        no_fill_count = sum(1 for item in recent_attempts if item.attempt_status in {'NO_FILL', 'FAILED'})
        if no_fill_count >= 12:
            incident = _upsert_incident(
                dedupe_key='execution:no-fill-anomaly',
                incident_type=IncidentType.EXECUTION_ANOMALY,
                severity=IncidentSeverity.HIGH,
                title='Execution anomaly detected',
                summary=f'No-fill/failed attempts={no_fill_count} over last {len(recent_attempts)} attempts.',
                source_app='execution_simulator',
                metadata={'no_fill_count': no_fill_count, 'sample_size': len(recent_attempts)},
            )
            detected_ids.append(incident.id)

    pending_queue = OperatorQueueItem.objects.filter(status=OperatorQueueStatus.PENDING).count()
    if pending_queue >= 20:
        incident = _upsert_incident(
            dedupe_key='queue:pressure-high',
            incident_type=IncidentType.QUEUE_PRESSURE,
            severity=IncidentSeverity.HIGH,
            title='Operator queue pressure is high',
            summary=f'Pending queue items reached {pending_queue}.',
            source_app='operator_queue',
            metadata={'pending_queue': pending_queue},
        )
        detected_ids.append(incident.id)

    runtime_state = get_runtime_state()
    safety = get_safety_status()
    if safety.get('kill_switch_enabled') or safety.get('hard_stop_active'):
        incident = _upsert_incident(
            dedupe_key='safety:block-active',
            incident_type=IncidentType.SAFETY_BLOCK,
            severity=IncidentSeverity.CRITICAL,
            title='Safety block is active',
            summary=f"Safety status={safety.get('status')} kill_switch={safety.get('kill_switch_enabled')} hard_stop={safety.get('hard_stop_active')}.",
            source_app='safety_guard',
            metadata={'safety_status': safety.get('status')},
        )
        detected_ids.append(incident.id)

    if runtime_state.current_mode != 'OBSERVE_ONLY' and (safety.get('kill_switch_enabled') or safety.get('hard_stop_active')):
        incident = _upsert_incident(
            dedupe_key='runtime:conflict-with-safety',
            incident_type=IncidentType.RUNTIME_CONFLICT,
            severity=IncidentSeverity.HIGH,
            title='Runtime and safety posture conflict',
            summary=f'Runtime mode {runtime_state.current_mode} conflicts with blocking safety state.',
            source_app='runtime_governor',
            metadata={'runtime_mode': runtime_state.current_mode, 'safety_status': safety.get('status')},
        )
        detected_ids.append(incident.id)

    llm_status = build_llm_status()
    if llm_status.get('enabled') and not llm_status.get('reachable'):
        incident = _upsert_incident(
            dedupe_key='llm:unavailable',
            incident_type=IncidentType.LLM_UNAVAILABLE,
            severity=IncidentSeverity.WARNING,
            title='Local LLM unavailable',
            summary=llm_status.get('message') or 'LLM is unreachable.',
            source_app='llm_local',
            metadata=llm_status,
        )
        detected_ids.append(incident.id)

    stale_unembedded = MemoryDocument.objects.filter(embedded_at__isnull=True, created_at__lt=now - timedelta(hours=6)).count()
    if stale_unembedded >= 10:
        incident = _upsert_incident(
            dedupe_key='memory:indexing-failure-pattern',
            incident_type=IncidentType.MEMORY_INDEX_FAILURE,
            severity=IncidentSeverity.WARNING,
            title='Memory indexing lag/failure pattern',
            summary=f'{stale_unembedded} memory documents still missing embeddings.',
            source_app='memory_retrieval',
            metadata={'stale_unembedded_docs': stale_unembedded},
        )
        detected_ids.append(incident.id)

    recent_delivery_failures = NotificationDelivery.objects.filter(
        created_at__gte=now - timedelta(hours=2),
        delivery_status=NotificationDeliveryStatus.FAILED,
    ).count()
    if recent_delivery_failures >= 5:
        incident = _upsert_incident(
            dedupe_key='notifications:delivery-failure',
            incident_type=IncidentType.ALERT_DELIVERY_FAILURE,
            severity=IncidentSeverity.HIGH,
            title='Critical notification delivery failure',
            summary=f'Notification delivery failed {recent_delivery_failures} times in the last 2h.',
            source_app='notification_center',
            metadata={'failure_count': recent_delivery_failures},
        )
        detected_ids.append(incident.id)

    return {
        'detected_count': len(detected_ids),
        'incident_ids': detected_ids,
    }

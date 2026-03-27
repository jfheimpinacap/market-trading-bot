from __future__ import annotations

from django.utils import timezone

from apps.incident_commander.models import IncidentAction, IncidentActionStatus, IncidentRecord, IncidentStatus
from apps.incident_commander.services.degraded_mode import apply_degraded_mode, reset_degraded_mode
from apps.incident_commander.services.policies import get_policy_for_incident
from apps.incident_commander.services.recovery import run_recovery_for_incident
from apps.mission_control.services import pause_session
from apps.operator_alerts.services.alerts import AlertEmitPayload, emit_alert
from apps.operator_queue.models import OperatorQueueItem, OperatorQueuePriority, OperatorQueueSource, OperatorQueueStatus, OperatorQueueType
from apps.rollout_manager.services import get_current_rollout_run, rollback_run


def _record_action(*, incident: IncidentRecord, action_type: str, status: str, rationale: str, metadata: dict | None = None) -> IncidentAction:
    return IncidentAction.objects.create(
        incident=incident,
        action_type=action_type,
        action_status=status,
        rationale=rationale,
        metadata=metadata or {},
    )


def _apply_single_action(*, incident: IncidentRecord, action_type: str) -> None:
    if action_type == 'pause_mission_control':
        try:
            pause_session()
            _record_action(incident=incident, action_type=action_type, status=IncidentActionStatus.APPLIED, rationale='Mission control paused due to recurring failures.')
        except Exception as exc:
            _record_action(incident=incident, action_type=action_type, status=IncidentActionStatus.SKIPPED, rationale=f'Pause skipped: {exc}')
    elif action_type == 'trigger_rollout_rollback':
        run = get_current_rollout_run()
        if run:
            rollback_run(run=run, reason=f'Incident #{incident.id} forced conservative rollback.', actor='incident_commander')
            _record_action(incident=incident, action_type=action_type, status=IncidentActionStatus.APPLIED, rationale='Active rollout rolled back by guardrail incident.', metadata={'run_id': run.id})
        else:
            _record_action(incident=incident, action_type=action_type, status=IncidentActionStatus.SKIPPED, rationale='No active rollout run to rollback.')
    elif action_type == 'send_critical_notification':
        alert = emit_alert(AlertEmitPayload(
            alert_type='anomaly',
            severity='critical' if incident.severity == 'critical' else 'high',
            title=f'Incident {incident.incident_type} requires attention',
            summary=incident.summary or incident.title,
            source='runtime',
            dedupe_key=f'incident:{incident.id}',
            related_object_type='incident_record',
            related_object_id=str(incident.id),
            metadata={'incident_status': incident.status},
        ))
        _record_action(incident=incident, action_type=action_type, status=IncidentActionStatus.APPLIED, rationale='Critical alert emitted for incident.', metadata={'alert_id': alert.id})
    elif action_type == 'queue_manual_review':
        item = OperatorQueueItem.objects.create(
            status=OperatorQueueStatus.PENDING,
            source=OperatorQueueSource.SAFETY,
            queue_type=OperatorQueueType.BLOCKED_REVIEW,
            priority=OperatorQueuePriority.HIGH if incident.severity != 'critical' else OperatorQueuePriority.CRITICAL,
            headline=f'Incident review required: {incident.incident_type}',
            summary=incident.summary,
            rationale='Incident commander requested manual operator review.',
            metadata={'incident_id': incident.id, 'incident_status': incident.status},
        )
        _record_action(incident=incident, action_type=action_type, status=IncidentActionStatus.APPLIED, rationale='Manual review enqueued.', metadata={'queue_item_id': item.id})
    elif action_type == 'attempt_recovery':
        run = run_recovery_for_incident(incident=incident)
        _record_action(incident=incident, action_type=action_type, status=IncidentActionStatus.APPLIED if run.run_status in {'SUCCESS', 'SKIPPED'} else IncidentActionStatus.FAILED, rationale=run.summary, metadata={'recovery_run_id': run.id, 'recovery_status': run.run_status})
    else:
        _record_action(incident=incident, action_type=action_type, status=IncidentActionStatus.APPLIED, rationale='Policy action registered.', metadata={'paper_demo_only': True})


def mitigate_incident(*, incident: IncidentRecord) -> IncidentRecord:
    directive = get_policy_for_incident(incident_type=incident.incident_type)

    incident.status = directive.incident_status
    incident.metadata = {
        **(incident.metadata or {}),
        'mitigated_at': timezone.now().isoformat(),
        'policy_state': directive.degraded_state,
        'policy_actions': directive.actions,
    }
    incident.save(update_fields=['status', 'metadata', 'updated_at'])

    if directive.degraded_state:
        apply_degraded_mode(
            state_code=directive.degraded_state,
            reason=f'Incident #{incident.id}: {incident.incident_type}',
            degraded_modules=[incident.source_app],
            disabled_actions=['auto_execute'] if 'disable_auto_execute' in directive.actions else [],
            mission_control_paused='pause_mission_control' in directive.actions,
            auto_execution_enabled='disable_auto_execute' not in directive.actions,
            rollout_enabled='trigger_rollout_rollback' not in directive.actions,
            metadata={'incident_id': incident.id},
        )

    for action in directive.actions:
        _apply_single_action(incident=incident, action_type=action)

    return incident


def resolve_incident(*, incident: IncidentRecord, resolution_note: str = '') -> IncidentRecord:
    incident.status = IncidentStatus.RESOLVED
    incident.metadata = {
        **(incident.metadata or {}),
        'resolved_at': timezone.now().isoformat(),
        'resolution_note': resolution_note or 'Incident resolved by conservative operator/system action.',
    }
    incident.save(update_fields=['status', 'metadata', 'updated_at'])
    _record_action(incident=incident, action_type='mark_resolved', status=IncidentActionStatus.APPLIED, rationale=resolution_note or 'Marked as resolved.')

    if not IncidentRecord.objects.exclude(pk=incident.pk).filter(status__in=[IncidentStatus.OPEN, IncidentStatus.MITIGATING, IncidentStatus.DEGRADED, IncidentStatus.RECOVERING, IncidentStatus.ESCALATED]).exists():
        reset_degraded_mode(reason='All active incidents resolved.')

    return incident

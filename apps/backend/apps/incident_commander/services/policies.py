from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Count

from apps.incident_commander.models import IncidentRecord, IncidentSeverity, IncidentStatus, IncidentType


@dataclass
class MitigationDirective:
    incident_status: str
    degraded_state: str | None
    actions: list[str]


INCIDENT_POLICY: dict[str, MitigationDirective] = {
    IncidentType.ROLLOUT_GUARDRAIL: MitigationDirective(
        incident_status=IncidentStatus.DEGRADED,
        degraded_state='rollout_disabled',
        actions=['trigger_rollout_rollback', 'send_critical_notification', 'queue_manual_review'],
    ),
    IncidentType.MISSION_CONTROL_FAILURE: MitigationDirective(
        incident_status=IncidentStatus.MITIGATING,
        degraded_state='mission_control_paused',
        actions=['pause_mission_control', 'send_critical_notification', 'queue_manual_review'],
    ),
    IncidentType.STALE_DATA: MitigationDirective(
        incident_status=IncidentStatus.DEGRADED,
        degraded_state='execution_degraded',
        actions=['disable_auto_execute', 'force_defensive_profile', 'send_critical_notification'],
    ),
    IncidentType.QUEUE_PRESSURE: MitigationDirective(
        incident_status=IncidentStatus.DEGRADED,
        degraded_state='auto_execute_disabled',
        actions=['disable_auto_execute', 'queue_manual_review'],
    ),
    IncidentType.LLM_UNAVAILABLE: MitigationDirective(
        incident_status=IncidentStatus.DEGRADED,
        degraded_state='research_degraded',
        actions=['skip_research_step', 'attempt_recovery'],
    ),
    IncidentType.SAFETY_BLOCK: MitigationDirective(
        incident_status=IncidentStatus.ESCALATED,
        degraded_state='defensive_only',
        actions=['force_defensive_profile', 'send_critical_notification'],
    ),
    IncidentType.RUNTIME_CONFLICT: MitigationDirective(
        incident_status=IncidentStatus.DEGRADED,
        degraded_state='defensive_only',
        actions=['disable_auto_execute', 'queue_manual_review'],
    ),
    IncidentType.EXECUTION_ANOMALY: MitigationDirective(
        incident_status=IncidentStatus.MITIGATING,
        degraded_state='execution_degraded',
        actions=['disable_auto_execute', 'attempt_recovery', 'queue_manual_review'],
    ),
    IncidentType.MEMORY_INDEX_FAILURE: MitigationDirective(
        incident_status=IncidentStatus.RECOVERING,
        degraded_state='research_degraded',
        actions=['attempt_recovery'],
    ),
    IncidentType.ALERT_DELIVERY_FAILURE: MitigationDirective(
        incident_status=IncidentStatus.MITIGATING,
        degraded_state='defensive_only',
        actions=['rebuild_alerts', 'send_critical_notification'],
    ),
}


def get_policy_for_incident(*, incident_type: str) -> MitigationDirective:
    return INCIDENT_POLICY.get(
        incident_type,
        MitigationDirective(
            incident_status=IncidentStatus.MITIGATING,
            degraded_state='defensive_only',
            actions=['queue_manual_review'],
        ),
    )


def summarize_incidents() -> dict:
    open_statuses = [
        IncidentStatus.OPEN,
        IncidentStatus.MITIGATING,
        IncidentStatus.DEGRADED,
        IncidentStatus.RECOVERING,
        IncidentStatus.ESCALATED,
    ]
    queryset = IncidentRecord.objects.filter(status__in=open_statuses)
    return {
        'active_incidents': queryset.count(),
        'critical_active': queryset.filter(severity=IncidentSeverity.CRITICAL).count(),
        'high_active': queryset.filter(severity=IncidentSeverity.HIGH).count(),
        'warning_active': queryset.filter(severity=IncidentSeverity.WARNING).count(),
        'resolved_total': IncidentRecord.objects.filter(status=IncidentStatus.RESOLVED).count(),
        'by_type': list(queryset.values('incident_type').order_by('incident_type').annotate(count=Count('id'))),
    }

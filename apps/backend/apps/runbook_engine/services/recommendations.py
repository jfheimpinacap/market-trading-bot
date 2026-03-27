from apps.certification_board.models import CertificationLevel, CertificationRun
from apps.incident_commander.models import IncidentRecord, IncidentSeverity, IncidentStatus
from apps.operator_queue.services import build_queue_summary
from apps.rollout_manager.models import RolloutGuardrailEvent
from apps.runbook_engine.models import RunbookTemplate
from apps.execution_venue.models import VenueParityRun, VenueParityStatus


def recommend_runbooks(*, source_object_type: str | None = None, source_object_id: str | None = None) -> list[dict]:
    templates = {item.slug: item for item in RunbookTemplate.objects.filter(is_enabled=True)}
    recommendations: list[dict] = []

    critical_incident = IncidentRecord.objects.filter(status__in=[IncidentStatus.OPEN, IncidentStatus.ESCALATED], severity=IncidentSeverity.CRITICAL).order_by('-last_seen_at').first()
    if critical_incident and 'incident_mission_control_pause' in templates:
        recommendations.append({
            'template_slug': 'incident_mission_control_pause',
            'reason': 'Critical incident is open.',
            'source_object_type': 'incident',
            'source_object_id': str(critical_incident.id),
            'priority': 'CRITICAL',
        })

    guardrail_event = RolloutGuardrailEvent.objects.filter(severity__iexact='CRITICAL').order_by('-created_at').first()
    if guardrail_event and 'rollout_guardrail_response' in templates:
        recommendations.append({
            'template_slug': 'rollout_guardrail_response',
            'reason': 'Critical rollout guardrail breach detected.',
            'source_object_type': 'rollout_run',
            'source_object_id': str(guardrail_event.run_id),
            'priority': 'CRITICAL',
        })

    latest_cert = CertificationRun.objects.order_by('-created_at').first()
    if latest_cert and latest_cert.certification_level in [CertificationLevel.REMEDIATION_REQUIRED, CertificationLevel.RECERTIFICATION_REQUIRED] and 'certification_downgrade_review' in templates:
        recommendations.append({
            'template_slug': 'certification_downgrade_review',
            'reason': f'Certification level is {latest_cert.certification_level}.',
            'source_object_type': 'certification_run',
            'source_object_id': str(latest_cert.id),
            'priority': 'HIGH',
        })

    parity_gap = VenueParityRun.objects.filter(parity_status=VenueParityStatus.PARITY_GAP).order_by('-created_at').first()
    if parity_gap and 'venue_parity_gap_investigation' in templates:
        recommendations.append({
            'template_slug': 'venue_parity_gap_investigation',
            'reason': 'Venue parity gap detected.',
            'source_object_type': 'venue_parity_run',
            'source_object_id': str(parity_gap.id),
            'priority': 'HIGH',
        })

    queue_summary = build_queue_summary()
    if (queue_summary.get('high_priority_count') or 0) >= 5 and 'queue_pressure_relief' in templates:
        recommendations.append({
            'template_slug': 'queue_pressure_relief',
            'reason': f"High-priority queue items pending: {queue_summary.get('high_priority_count', 0)}.",
            'source_object_type': 'operator_queue',
            'source_object_id': 'summary',
            'priority': 'HIGH',
        })

    if source_object_type and source_object_id:
        recommendations = [item for item in recommendations if item['source_object_type'] == source_object_type and item['source_object_id'] == source_object_id] or recommendations

    return recommendations

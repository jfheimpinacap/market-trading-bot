from __future__ import annotations

from apps.approval_center.models import ApprovalRequest
from apps.autonomy_program.models import AutonomyProgramState, ProgramConcurrencyPosture
from apps.autonomy_program.services.rules import evaluate_concurrency_conflicts, get_active_campaigns_queryset
from apps.incident_commander.models import DegradedModeState, IncidentRecord


def _derive_posture(*, has_critical_incident: bool, has_degraded_mode: bool, conflict_count: int) -> str:
    if has_critical_incident:
        return ProgramConcurrencyPosture.FROZEN
    if has_degraded_mode and conflict_count > 0:
        return ProgramConcurrencyPosture.HIGH_RISK
    if has_degraded_mode or conflict_count > 0:
        return ProgramConcurrencyPosture.CONSTRAINED
    return ProgramConcurrencyPosture.NORMAL


def recompute_program_state() -> AutonomyProgramState:
    active_campaigns = list(get_active_campaigns_queryset())
    waiting_approval_count = ApprovalRequest.objects.filter(status='PENDING').count()
    observing_campaigns_count = sum(1 for campaign in active_campaigns if any(step.status == 'OBSERVING' for step in campaign.steps.all()))
    blocked_campaigns_count = sum(1 for campaign in active_campaigns if campaign.status == 'BLOCKED')
    latest_degraded = DegradedModeState.objects.order_by('-updated_at', '-id').first()
    has_degraded_mode = bool(latest_degraded and latest_degraded.state != 'normal')
    has_critical_incident = IncidentRecord.objects.filter(status__in=['OPEN', 'DEGRADED', 'ESCALATED'], severity='critical').exists()

    rule_eval = evaluate_concurrency_conflicts(active_campaigns=active_campaigns)
    locked_domains = sorted({domain for domains in rule_eval['active_domains'].values() for domain in domains})
    degraded_domains = set((latest_degraded.degraded_modules if latest_degraded else []) or [])
    degraded_domains_count = len(degraded_domains)
    posture = _derive_posture(
        has_critical_incident=has_critical_incident,
        has_degraded_mode=has_degraded_mode,
        conflict_count=len(rule_eval['conflicts']),
    )

    return AutonomyProgramState.objects.create(
        active_campaigns_count=len(active_campaigns),
        blocked_campaigns_count=blocked_campaigns_count,
        waiting_approval_count=waiting_approval_count,
        observing_campaigns_count=observing_campaigns_count,
        degraded_domains_count=degraded_domains_count,
        locked_domains=locked_domains,
        concurrency_posture=posture,
        metadata={
            'critical_incident_active': has_critical_incident,
            'degraded_state': latest_degraded.state if latest_degraded else 'normal',
            'max_active_campaigns': rule_eval['max_active_campaigns'],
            'conflicts': rule_eval['conflicts'],
            'degraded_domains': sorted(degraded_domains),
        },
    )


def build_program_state_payload() -> dict:
    latest = AutonomyProgramState.objects.order_by('-created_at', '-id').first() or recompute_program_state()
    return {
        'state': latest,
        'conflicts': latest.metadata.get('conflicts', []),
        'max_active_campaigns': latest.metadata.get('max_active_campaigns', 0),
        'critical_incident_active': latest.metadata.get('critical_incident_active', False),
    }

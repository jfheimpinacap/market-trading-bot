from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.approval_center.models import ApprovalRequestStatus
from apps.autonomy_campaign.models import AutonomyCampaign, AutonomyCampaignStatus
from apps.autonomy_launch.models import LaunchAuthorization, LaunchAuthorizationStatus
from apps.autonomy_program.models import ProgramConcurrencyPosture
from apps.autonomy_scheduler.models import ChangeWindowStatus
from apps.incident_commander.models import DegradedModeState, IncidentRecord


@dataclass
class RevalidationResult:
    readiness_status: str
    reason_codes: list[str]
    blockers: list[str]
    incident_impact: int
    degraded_impact: int
    domain_conflict: bool
    rollout_pressure: int


def _campaign_domains(campaign: AutonomyCampaign) -> list[str]:
    return sorted(set((campaign.metadata or {}).get('domains', []) or []))


def revalidate_campaign_dispatch(
    *,
    campaign: AutonomyCampaign,
    authorization: LaunchAuthorization | None,
    program_posture: str,
    active_window_status: str,
    locked_domains: list[str],
) -> RevalidationResult:
    now = timezone.now()
    blockers: list[str] = []
    reason_codes: list[str] = []

    if authorization is None:
        blockers.append('Missing launch authorization.')
        reason_codes.append('AUTHORIZATION_MISSING')
        return RevalidationResult('BLOCKED', reason_codes, blockers, 0, 0, False, 0)

    if authorization.authorization_status != LaunchAuthorizationStatus.AUTHORIZED:
        blockers.append(f'Launch authorization is {authorization.authorization_status}.')
        reason_codes.append('AUTHORIZATION_NOT_AUTHORIZED')

    if authorization.expires_at and authorization.expires_at <= now:
        blockers.append('Launch authorization has expired.')
        reason_codes.append('AUTHORIZATION_EXPIRED')

    if authorization.requires_approval and authorization.approved_request_id:
        approval_status = authorization.approved_request.status
        if approval_status != ApprovalRequestStatus.APPROVED:
            blockers.append(f'Approval request is {approval_status}.')
            reason_codes.append('APPROVAL_NOT_APPROVED')

    if campaign.status in {AutonomyCampaignStatus.RUNNING, AutonomyCampaignStatus.COMPLETED}:
        blockers.append(f'Campaign is already {campaign.status}.')
        reason_codes.append('CAMPAIGN_ALREADY_STARTED')

    if program_posture == ProgramConcurrencyPosture.FROZEN:
        blockers.append('Program posture is FROZEN.')
        reason_codes.append('PROGRAM_FROZEN')

    if active_window_status in {ChangeWindowStatus.CLOSED, ChangeWindowStatus.FROZEN}:
        blockers.append(f'Active window status is {active_window_status}.')
        reason_codes.append('WINDOW_NOT_DISPATCHABLE')
    elif active_window_status == ChangeWindowStatus.UPCOMING:
        blockers.append('Safe start window is UPCOMING.')
        reason_codes.append('WAIT_FOR_WINDOW')

    campaign_domains = _campaign_domains(campaign)
    locked = sorted(set(campaign_domains).intersection(set(locked_domains)))
    domain_conflict = bool(locked)
    if domain_conflict:
        blockers.append(f'Domain conflict with locks: {", ".join(locked)}.')
        reason_codes.append('DOMAIN_CONFLICT')

    critical_incident_count = IncidentRecord.objects.filter(status__in=['OPEN', 'DEGRADED', 'ESCALATED'], severity='critical').count()
    degraded_state = DegradedModeState.objects.order_by('-updated_at', '-id').first()
    degraded_domains = set((degraded_state.degraded_modules if degraded_state else []) or [])
    degraded_impact = len(set(campaign_domains).intersection(degraded_domains))
    rollout_pressure = 1 if degraded_state and not degraded_state.rollout_enabled else 0

    if critical_incident_count > 0:
        blockers.append('Critical incident is active.')
        reason_codes.append('CRITICAL_INCIDENT_ACTIVE')

    if degraded_impact > 0:
        blockers.append('Campaign domains are in degraded mode.')
        reason_codes.append('DEGRADED_DOMAIN_IMPACT')

    if rollout_pressure > 0:
        reason_codes.append('ROLLOUT_PRESSURE')

    if 'AUTHORIZATION_EXPIRED' in reason_codes:
        readiness_status = 'EXPIRED'
    elif any(code in reason_codes for code in ['WAIT_FOR_WINDOW']):
        readiness_status = 'WAITING'
    elif blockers:
        readiness_status = 'BLOCKED'
    else:
        readiness_status = 'READY_TO_DISPATCH'

    return RevalidationResult(
        readiness_status=readiness_status,
        reason_codes=reason_codes,
        blockers=blockers,
        incident_impact=critical_incident_count,
        degraded_impact=degraded_impact,
        domain_conflict=domain_conflict,
        rollout_pressure=rollout_pressure,
    )

from __future__ import annotations

from apps.approval_center.models import ApprovalRequest, ApprovalRequestStatus
from apps.autonomy_campaign.models import AutonomyCampaignCheckpoint, AutonomyCampaignCheckpointStatus
from apps.autonomy_program.models import ProgramConcurrencyPosture
from apps.autonomy_rollout.models import AutonomyRolloutRun, AutonomyRolloutStatus
from apps.autonomy_scheduler.models import ChangeWindowStatus
from apps.incident_commander.models import DegradedModeState, IncidentRecord


def evaluate_preflight(*, admission, program_state, active_window) -> dict:
    campaign = admission.campaign
    metadata = campaign.metadata or {}
    domain_set = set(metadata.get('domains') or [])

    unresolved_checkpoints = AutonomyCampaignCheckpoint.objects.filter(
        campaign=campaign,
        status=AutonomyCampaignCheckpointStatus.OPEN,
    ).count()
    unresolved_approvals = ApprovalRequest.objects.filter(
        status=ApprovalRequestStatus.PENDING,
        metadata__autonomy_campaign_id=campaign.id,
    ).count()

    dependency_blocked = False
    for dep_id in metadata.get('depends_on_campaigns', []):
        dep = admission.__class__.objects.select_related('campaign').filter(campaign_id=dep_id).first()
        if dep and dep.campaign.status not in ['COMPLETED']:
            dependency_blocked = True
            break

    locked_domains = set((program_state.locked_domains if program_state else []) or [])
    domain_conflict = bool(domain_set.intersection(locked_domains))

    incident_impact = IncidentRecord.objects.filter(
        status__in=['OPEN', 'DEGRADED', 'ESCALATED'],
        severity__in=['critical', 'high'],
    ).filter(source_app__in=domain_set).count() if domain_set else 0
    if not domain_set:
        incident_impact = IncidentRecord.objects.filter(status__in=['OPEN', 'DEGRADED', 'ESCALATED'], severity='critical').count()

    degraded_state = DegradedModeState.objects.order_by('-updated_at', '-id').first()
    degraded_modules = set((degraded_state.degraded_modules if degraded_state else []) or [])
    degraded_impact = len(domain_set.intersection(degraded_modules))

    rollout_observation_impact = AutonomyRolloutRun.objects.filter(
        domain__slug__in=domain_set,
        rollout_status__in=[
            AutonomyRolloutStatus.CAUTION,
            AutonomyRolloutStatus.FREEZE_RECOMMENDED,
            AutonomyRolloutStatus.ROLLBACK_RECOMMENDED,
        ],
    ).count()

    blockers: list[str] = []
    reason_codes: list[str] = []
    requires_approval = False

    if admission.status not in ['ADMITTED', 'READY']:
        blockers.append('Campaign is not admitted/ready for launch.')
        reason_codes.append('NOT_ADMITTED')

    if program_state and program_state.concurrency_posture == ProgramConcurrencyPosture.FROZEN:
        blockers.append('Program posture is FROZEN.')
        reason_codes.append('PROGRAM_FROZEN')

    if program_state and program_state.concurrency_posture == ProgramConcurrencyPosture.HIGH_RISK:
        reason_codes.append('PROGRAM_HIGH_RISK')
        requires_approval = True

    if active_window is None or active_window.status != ChangeWindowStatus.OPEN:
        blockers.append('No OPEN start window is active.')
        reason_codes.append('WINDOW_NOT_OPEN')

    if domain_conflict:
        blockers.append('Campaign domains conflict with active locked domains.')
        reason_codes.append('DOMAIN_CONFLICT')

    if dependency_blocked:
        blockers.append('One or more campaign dependencies are not stabilized/completed.')
        reason_codes.append('DEPENDENCY_BLOCKED')

    if unresolved_checkpoints > 0:
        blockers.append('Campaign has unresolved launch checkpoints.')
        reason_codes.append('CHECKPOINTS_PENDING')

    if unresolved_approvals > 0:
        requires_approval = True
        blockers.append('Campaign has unresolved approvals.')
        reason_codes.append('APPROVALS_PENDING')

    if incident_impact > 0:
        blockers.append('Relevant incidents are active for this campaign scope.')
        reason_codes.append('INCIDENT_IMPACT')

    if degraded_impact > 0:
        blockers.append('Degraded mode affects one or more campaign domains.')
        reason_codes.append('DEGRADED_IMPACT')

    if rollout_observation_impact > 0:
        blockers.append('Rollout warning/observation pressure detected on campaign domains.')
        reason_codes.append('ROLLOUT_PRESSURE')

    return {
        'campaign': campaign,
        'admission': admission,
        'program_posture': program_state.concurrency_posture if program_state else 'NORMAL',
        'active_window_status': active_window.status if active_window else 'CLOSED',
        'unresolved_checkpoints_count': unresolved_checkpoints,
        'unresolved_approvals_count': unresolved_approvals,
        'dependency_blocked': dependency_blocked,
        'domain_conflict': domain_conflict,
        'incident_impact': incident_impact,
        'degraded_impact': degraded_impact,
        'rollout_observation_impact': rollout_observation_impact,
        'blockers': blockers,
        'reason_codes': reason_codes,
        'requires_approval': requires_approval,
        'impacted_domains': sorted(domain_set),
    }

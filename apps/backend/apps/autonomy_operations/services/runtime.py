from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Prefetch
from django.utils import timezone

from apps.approval_center.models import ApprovalRequest
from apps.autonomy_campaign.models import (
    AutonomyCampaign,
    AutonomyCampaignCheckpoint,
    AutonomyCampaignCheckpointStatus,
    AutonomyCampaignStep,
    AutonomyCampaignStepStatus,
)
from apps.autonomy_rollout.models import AutonomyRolloutRun
from apps.incident_commander.models import DegradedModeState, IncidentRecord

ACTIVE_CAMPAIGN_STATUSES = ['RUNNING', 'PAUSED', 'BLOCKED']


@dataclass
class RuntimeContext:
    campaign: AutonomyCampaign
    started_at: timezone.datetime | None
    current_step: AutonomyCampaignStep | None
    current_checkpoint: AutonomyCampaignCheckpoint | None
    open_checkpoints_count: int
    pending_approvals_count: int
    blocked_steps_count: int
    incident_impact: int
    degraded_impact: int
    rollout_observation_impact: int
    blockers: list[str]
    metadata: dict


def list_active_campaigns():
    return (
        AutonomyCampaign.objects.filter(status__in=ACTIVE_CAMPAIGN_STATUSES)
        .prefetch_related(
            Prefetch('steps', queryset=AutonomyCampaignStep.objects.select_related('domain').order_by('step_order')),
            Prefetch('checkpoints', queryset=AutonomyCampaignCheckpoint.objects.select_related('step').order_by('-created_at', '-id')),
        )
        .order_by('-updated_at', '-id')
    )


def _approval_ids(open_checkpoints: list[AutonomyCampaignCheckpoint]) -> list[int]:
    ids: list[int] = []
    for checkpoint in open_checkpoints:
        maybe = (checkpoint.metadata or {}).get('approval_request_id')
        if maybe:
            ids.append(int(maybe))
    return ids


def build_runtime_context(campaign: AutonomyCampaign) -> RuntimeContext:
    steps = list(campaign.steps.all())
    checkpoints = list(campaign.checkpoints.all())
    running_step = next((step for step in steps if step.status == AutonomyCampaignStepStatus.RUNNING), None)
    current_step = running_step or next(
        (
            step
            for step in steps
            if step.status in {AutonomyCampaignStepStatus.WAITING_APPROVAL, AutonomyCampaignStepStatus.OBSERVING, AutonomyCampaignStepStatus.READY, AutonomyCampaignStepStatus.PENDING}
        ),
        None,
    )
    open_checkpoints = [checkpoint for checkpoint in checkpoints if checkpoint.status == AutonomyCampaignCheckpointStatus.OPEN]
    current_checkpoint = next((item for item in open_checkpoints if current_step and item.step_id == current_step.id), None) or (open_checkpoints[0] if open_checkpoints else None)

    approval_ids = _approval_ids(open_checkpoints)
    pending_approvals_count = ApprovalRequest.objects.filter(pk__in=approval_ids, status__in=['PENDING', 'ESCALATED']).count() if approval_ids else 0

    domains = (campaign.metadata or {}).get('domains') or []
    incidents = list(IncidentRecord.objects.filter(status__in=['OPEN', 'MITIGATING', 'DEGRADED', 'ESCALATED']).order_by('-last_seen_at', '-id')[:200])
    incident_impact = 0
    for incident in incidents:
        if incident.related_object_type == 'autonomy_campaign' and str(incident.related_object_id) == str(campaign.id):
            incident_impact += 1
            continue
        incident_domains = (incident.metadata or {}).get('domains') or []
        if domains and any(domain in incident_domains for domain in domains):
            incident_impact += 1

    degraded = DegradedModeState.objects.order_by('-updated_at', '-id').first()
    degraded_impact = 0
    if degraded and degraded.state != 'normal':
        degraded_impact = 1 + len(degraded.degraded_modules or [])

    rollout_ids = [step.metadata.get('autonomy_rollout_run_id') for step in steps if (step.metadata or {}).get('autonomy_rollout_run_id')]
    rollout_observation_impact = AutonomyRolloutRun.objects.filter(pk__in=rollout_ids, rollout_status__in=['OBSERVING', 'CAUTION', 'FREEZE_RECOMMENDED', 'ROLLBACK_RECOMMENDED']).count() if rollout_ids else 0

    blockers: list[str] = []
    if pending_approvals_count:
        blockers.append('pending_approvals')
    if open_checkpoints:
        blockers.append('open_checkpoints')
    if campaign.status == 'BLOCKED' or campaign.blocked_steps:
        blockers.append('blocked_steps')
    if incident_impact:
        blockers.append('incident_pressure')
    if degraded_impact:
        blockers.append('degraded_mode')
    if rollout_observation_impact:
        blockers.append('rollout_pressure')

    started_at = campaign.metadata.get('started_at') if isinstance(campaign.metadata, dict) else None

    return RuntimeContext(
        campaign=campaign,
        started_at=started_at,
        current_step=current_step,
        current_checkpoint=current_checkpoint,
        open_checkpoints_count=len(open_checkpoints),
        pending_approvals_count=pending_approvals_count,
        blocked_steps_count=campaign.blocked_steps,
        incident_impact=incident_impact,
        degraded_impact=degraded_impact,
        rollout_observation_impact=rollout_observation_impact,
        blockers=blockers,
        metadata={'domains': domains},
    )

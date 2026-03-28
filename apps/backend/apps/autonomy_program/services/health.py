from __future__ import annotations

from apps.approval_center.models import ApprovalRequest
from apps.autonomy_campaign.models import AutonomyCampaign, AutonomyCampaignStatus
from apps.autonomy_program.models import CampaignHealthSnapshot, CampaignHealthStatus
from apps.autonomy_rollout.models import AutonomyRolloutRun, AutonomyRolloutStatus
from apps.incident_commander.models import DegradedModeState, IncidentRecord


def _status_from_score(score: int, blocked_checkpoints: int, incident_impact: int) -> str:
    if blocked_checkpoints > 0:
        return CampaignHealthStatus.BLOCKED
    if incident_impact > 0 or score <= 45:
        return CampaignHealthStatus.AT_RISK
    if score <= 75:
        return CampaignHealthStatus.CAUTION
    return CampaignHealthStatus.HEALTHY


def build_campaign_health_snapshots() -> list[CampaignHealthSnapshot]:
    campaigns = AutonomyCampaign.objects.filter(status__in=[AutonomyCampaignStatus.RUNNING, AutonomyCampaignStatus.BLOCKED, AutonomyCampaignStatus.PAUSED]).prefetch_related('steps__domain', 'checkpoints')
    latest_degraded = DegradedModeState.objects.order_by('-updated_at', '-id').first()
    degraded_domains = set((latest_degraded.degraded_modules if latest_degraded else []) or [])

    snapshots: list[CampaignHealthSnapshot] = []
    for campaign in campaigns:
        domain_slugs = {step.domain.slug for step in campaign.steps.all() if step.domain}
        blocked_checkpoints = campaign.checkpoints.filter(status='OPEN').count()
        open_approvals = ApprovalRequest.objects.filter(status='PENDING', source_object_id=str(campaign.id)).count()
        rollout_warnings = AutonomyRolloutRun.objects.filter(
            domain__slug__in=domain_slugs,
            rollout_status__in=[AutonomyRolloutStatus.CAUTION, AutonomyRolloutStatus.FREEZE_RECOMMENDED, AutonomyRolloutStatus.ROLLBACK_RECOMMENDED],
        ).count()
        incident_impact = IncidentRecord.objects.filter(
            status__in=['OPEN', 'DEGRADED', 'ESCALATED'],
            related_object_type='autonomy_campaign',
            related_object_id=str(campaign.id),
        ).count()
        degraded_impact = len(domain_slugs.intersection(degraded_domains))

        score = max(0, 100 - (blocked_checkpoints * 25) - (open_approvals * 15) - (rollout_warnings * 12) - (incident_impact * 25) - (degraded_impact * 15))
        status = _status_from_score(score=score, blocked_checkpoints=blocked_checkpoints, incident_impact=incident_impact)
        snapshot = CampaignHealthSnapshot.objects.create(
            campaign=campaign,
            active_wave=campaign.current_wave,
            domain_count=len(domain_slugs),
            blocked_checkpoints=blocked_checkpoints,
            open_approvals=open_approvals,
            rollout_warnings=rollout_warnings,
            incident_impact=incident_impact,
            degraded_impact=degraded_impact,
            health_score=score,
            health_status=status,
            metadata={
                'domains': sorted(domain_slugs),
                'campaign_status': campaign.status,
            },
        )
        snapshots.append(snapshot)

    return snapshots

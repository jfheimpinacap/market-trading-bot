from __future__ import annotations

from dataclasses import dataclass

from apps.approval_center.models import ApprovalRequest
from apps.autonomy_campaign.models import AutonomyCampaign, AutonomyCampaignCheckpoint
from apps.autonomy_intervention.models import CampaignInterventionAction, CampaignInterventionRequest, InterventionOutcome
from apps.autonomy_operations.models import CampaignRuntimeSnapshot
from apps.incident_commander.models import IncidentRecord


@dataclass
class RecoveryCandidateContext:
    campaign: AutonomyCampaign
    runtime: CampaignRuntimeSnapshot | None
    last_request: CampaignInterventionRequest | None
    last_action: CampaignInterventionAction | None
    last_outcome: InterventionOutcome | None
    pending_approvals_count: int
    pending_checkpoints_count: int
    incident_impact: int
    degraded_impact: int
    rollout_observation_impact: int


def _campaign_ids_from_recent_intervention(limit: int = 200) -> set[int]:
    request_ids = CampaignInterventionRequest.objects.order_by('-created_at', '-id').values_list('campaign_id', flat=True)[:limit]
    return set(request_ids)


def _campaign_ids_from_recent_runtime(limit: int = 200) -> set[int]:
    runtime_ids = CampaignRuntimeSnapshot.objects.order_by('-created_at', '-id').values_list('campaign_id', flat=True)[:limit]
    return set(runtime_ids)


def list_recovery_candidate_campaigns() -> list[AutonomyCampaign]:
    direct_statuses = ['PAUSED', 'BLOCKED']
    ids = set(AutonomyCampaign.objects.filter(status__in=direct_statuses).values_list('id', flat=True))
    ids.update(_campaign_ids_from_recent_intervention())
    ids.update(_campaign_ids_from_recent_runtime())
    campaigns = AutonomyCampaign.objects.filter(id__in=ids).order_by('-updated_at', '-id')
    return list(campaigns)


def build_recovery_candidates() -> list[RecoveryCandidateContext]:
    contexts: list[RecoveryCandidateContext] = []
    for campaign in list_recovery_candidate_campaigns():
        runtime = CampaignRuntimeSnapshot.objects.filter(campaign=campaign).order_by('-created_at', '-id').first()
        last_request = CampaignInterventionRequest.objects.filter(campaign=campaign).order_by('-created_at', '-id').first()
        last_action = CampaignInterventionAction.objects.filter(campaign=campaign).order_by('-created_at', '-id').first()
        last_outcome = InterventionOutcome.objects.filter(action__campaign=campaign).order_by('-created_at', '-id').first()
        pending_approvals_count = ApprovalRequest.objects.filter(
            status='PENDING', metadata__autonomy_campaign_id=campaign.id
        ).count()
        pending_checkpoints_count = AutonomyCampaignCheckpoint.objects.filter(campaign=campaign, status='OPEN').count()
        open_incidents = IncidentRecord.objects.filter(
            related_object_type='autonomy_campaign', related_object_id=str(campaign.id), status__in=['OPEN', 'DEGRADED', 'ESCALATED', 'MITIGATING']
        )
        incident_impact = open_incidents.count()
        degraded_impact = open_incidents.filter(status='DEGRADED').count()
        rollout_observation_impact = 1 if pending_checkpoints_count > 0 else 0
        contexts.append(
            RecoveryCandidateContext(
                campaign=campaign,
                runtime=runtime,
                last_request=last_request,
                last_action=last_action,
                last_outcome=last_outcome,
                pending_approvals_count=pending_approvals_count,
                pending_checkpoints_count=pending_checkpoints_count,
                incident_impact=incident_impact,
                degraded_impact=degraded_impact,
                rollout_observation_impact=rollout_observation_impact,
            )
        )
    return contexts

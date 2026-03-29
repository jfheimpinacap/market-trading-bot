from __future__ import annotations

from dataclasses import dataclass

from apps.approval_center.models import ApprovalRequest
from apps.autonomy_campaign.models import AutonomyCampaign
from apps.autonomy_intervention.models import InterventionOutcome
from apps.autonomy_operations.models import CampaignRuntimeSnapshot
from apps.autonomy_recovery.models import RecoverySnapshot
from apps.incident_commander.models import IncidentRecord
from django.db import models


@dataclass
class DispositionCandidateContext:
    campaign: AutonomyCampaign
    recovery_snapshot: RecoverySnapshot | None
    last_intervention_outcome: InterventionOutcome | None
    last_runtime_snapshot: CampaignRuntimeSnapshot | None
    pending_approvals_count: int
    pending_checkpoints_count: int
    unresolved_incident_pressure: int


def build_disposition_candidates() -> list[DispositionCandidateContext]:
    campaigns = list(
        AutonomyCampaign.objects.filter(status__in=['COMPLETED', 'PAUSED', 'BLOCKED', 'ABORTED', 'FAILED', 'RUNNING'])
        .prefetch_related('checkpoints')
        .order_by('-updated_at', '-id')[:300]
    )
    campaign_ids = [campaign.id for campaign in campaigns]
    if not campaign_ids:
        return []

    recovery_map = {
        snapshot.campaign_id: snapshot
        for snapshot in RecoverySnapshot.objects.filter(campaign_id__in=campaign_ids).order_by('campaign_id', '-created_at')
    }
    outcome_map = {
        outcome.action.campaign_id: outcome
        for outcome in InterventionOutcome.objects.select_related('action')
        .filter(action__campaign_id__in=campaign_ids)
        .order_by('action__campaign_id', '-created_at')
    }
    runtime_map = {
        snapshot.campaign_id: snapshot
        for snapshot in CampaignRuntimeSnapshot.objects.filter(campaign_id__in=campaign_ids).order_by('campaign_id', '-created_at')
    }

    pending_approval_counts = {
        row['metadata__autonomy_campaign_id']: row['count']
        for row in ApprovalRequest.objects.filter(
            status='PENDING', metadata__autonomy_campaign_id__in=campaign_ids
        )
        .values('metadata__autonomy_campaign_id')
        .annotate(count=models.Count('id'))
    }
    unresolved_incident_counts = {
        row['related_object_id']: row['count']
        for row in IncidentRecord.objects.filter(
            related_object_type='autonomy_campaign',
            related_object_id__in=[str(item) for item in campaign_ids],
            status__in=['OPEN', 'DEGRADED'],
        )
        .values('related_object_id')
        .annotate(count=models.Count('id'))
    }

    contexts: list[DispositionCandidateContext] = []
    for campaign in campaigns:
        contexts.append(
            DispositionCandidateContext(
                campaign=campaign,
                recovery_snapshot=recovery_map.get(campaign.id),
                last_intervention_outcome=outcome_map.get(campaign.id),
                last_runtime_snapshot=runtime_map.get(campaign.id),
                pending_approvals_count=pending_approval_counts.get(campaign.id, 0),
                pending_checkpoints_count=campaign.checkpoints.filter(status='OPEN').count(),
                unresolved_incident_pressure=unresolved_incident_counts.get(str(campaign.id), 0),
            )
        )
    return contexts


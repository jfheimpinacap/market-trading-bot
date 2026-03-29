from __future__ import annotations

from dataclasses import dataclass

from django.db import models

from apps.approval_center.models import ApprovalRequest
from apps.autonomy_campaign.models import AutonomyCampaign, AutonomyCampaignCheckpoint
from apps.autonomy_disposition.models import CampaignDisposition
from apps.autonomy_intervention.models import CampaignInterventionAction
from apps.incident_commander.models import IncidentRecord


@dataclass
class CloseoutCandidate:
    campaign: AutonomyCampaign
    disposition: CampaignDisposition
    ready_for_closeout: bool
    requires_postmortem: bool
    requires_memory_index: bool
    requires_roadmap_feedback: bool
    unresolved_blockers: list[str]
    unresolved_approvals_count: int
    incident_history_level: str
    intervention_count: int
    metadata: dict


def _incident_history_level(incident_rows: list[IncidentRecord]) -> str:
    severe = [item for item in incident_rows if item.severity in {'high', 'critical'}]
    if len(severe) >= 2:
        return 'HIGH'
    if severe:
        return 'MEDIUM'
    return 'LOW'


def build_closeout_candidates() -> list[CloseoutCandidate]:
    dispositions = list(
        CampaignDisposition.objects.select_related('campaign')
        .filter(disposition_status__in=['READY', 'APPLIED', 'APPROVAL_REQUIRED', 'BLOCKED'])
        .order_by('campaign_id', '-created_at')
    )
    latest_by_campaign: dict[int, CampaignDisposition] = {}
    for disposition in dispositions:
        latest_by_campaign.setdefault(disposition.campaign_id, disposition)

    if not latest_by_campaign:
        return []

    campaign_ids = list(latest_by_campaign.keys())

    pending_approval_counts = {
        row['metadata__autonomy_campaign_id']: row['count']
        for row in ApprovalRequest.objects.filter(status='PENDING', metadata__autonomy_campaign_id__in=campaign_ids)
        .values('metadata__autonomy_campaign_id')
        .annotate(count=models.Count('id'))
    }
    open_checkpoint_counts = {
        row['campaign_id']: row['count']
        for row in AutonomyCampaignCheckpoint.objects.filter(campaign_id__in=campaign_ids, status='OPEN')
        .values('campaign_id')
        .annotate(count=models.Count('id'))
    }
    intervention_counts = {
        row['campaign_id']: row['count']
        for row in CampaignInterventionAction.objects.filter(campaign_id__in=campaign_ids)
        .values('campaign_id')
        .annotate(count=models.Count('id'))
    }

    incident_rows = list(
        IncidentRecord.objects.filter(
            related_object_type='autonomy_campaign',
            related_object_id__in=[str(item) for item in campaign_ids],
        ).order_by('related_object_id', '-created_at')
    )
    incidents_by_campaign: dict[str, list[IncidentRecord]] = {}
    for incident in incident_rows:
        incidents_by_campaign.setdefault(incident.related_object_id or '', []).append(incident)

    rows: list[CloseoutCandidate] = []
    for campaign_id, disposition in latest_by_campaign.items():
        campaign = disposition.campaign
        blockers = list(disposition.blockers)
        unresolved_approvals_count = pending_approval_counts.get(campaign_id, 0)
        if unresolved_approvals_count:
            blockers.append('pending_approval_requests')
        open_checkpoint_count = open_checkpoint_counts.get(campaign_id, 0)
        if open_checkpoint_count:
            blockers.append('open_checkpoints')

        incidents = incidents_by_campaign.get(str(campaign_id), [])
        incident_level = _incident_history_level(incidents)
        intervention_count = intervention_counts.get(campaign_id, 0)
        dependency_conflict = campaign.checkpoints.filter(checkpoint_type='DEPENDENCY_CONFLICT').exists()

        ready_for_closeout = disposition.disposition_status == 'APPLIED' and not blockers
        requires_postmortem = disposition.disposition_type in {'ABORTED', 'RETIRED'} and incident_level in {'MEDIUM', 'HIGH'}
        requires_memory_index = disposition.disposition_type in {'CLOSED', 'COMPLETED_RECORDED'} and ready_for_closeout
        requires_roadmap_feedback = dependency_conflict or intervention_count >= 2

        rows.append(
            CloseoutCandidate(
                campaign=campaign,
                disposition=disposition,
                ready_for_closeout=ready_for_closeout,
                requires_postmortem=requires_postmortem,
                requires_memory_index=requires_memory_index,
                requires_roadmap_feedback=requires_roadmap_feedback,
                unresolved_blockers=blockers,
                unresolved_approvals_count=unresolved_approvals_count,
                incident_history_level=incident_level,
                intervention_count=intervention_count,
                metadata={
                    'open_checkpoints_count': open_checkpoint_count,
                    'dependency_conflict': dependency_conflict,
                },
            )
        )

    return sorted(rows, key=lambda item: (not item.ready_for_closeout, -item.campaign.updated_at.timestamp()))

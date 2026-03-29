from __future__ import annotations

from apps.autonomy_intervention.models import CampaignInterventionAction
from apps.autonomy_operations.models import CampaignRuntimeSnapshot
from apps.autonomy_recovery.models import RecoverySnapshot
from apps.incident_commander.models import IncidentRecord

from apps.autonomy_closeout.services.candidates import CloseoutCandidate


def build_closeout_summary(candidate: CloseoutCandidate) -> dict:
    campaign = candidate.campaign
    latest_runtime = CampaignRuntimeSnapshot.objects.filter(campaign=campaign).order_by('-created_at', '-id').first()
    latest_recovery = RecoverySnapshot.objects.filter(campaign=campaign).order_by('-created_at', '-id').first()
    interventions = list(CampaignInterventionAction.objects.filter(campaign=campaign).order_by('-created_at', '-id')[:20])
    incidents = list(
        IncidentRecord.objects.filter(related_object_type='autonomy_campaign', related_object_id=str(campaign.id)).order_by('-created_at', '-id')[:20]
    )

    lifecycle_summary = {
        'campaign_status': campaign.status,
        'campaign_wave': campaign.current_wave,
        'total_steps': campaign.total_steps,
        'completed_steps': campaign.completed_steps,
        'blocked_steps': campaign.blocked_steps,
        'disposition_status': candidate.disposition.disposition_status,
        'disposition_reason_codes': candidate.disposition.reason_codes,
        'campaign_metadata': campaign.metadata,
    }
    incident_summary = {
        'count': len(incidents),
        'levels': candidate.incident_history_level,
        'recent': [
            {'id': item.id, 'severity': item.severity, 'status': item.status, 'title': item.title}
            for item in incidents[:5]
        ],
    }
    intervention_summary = {
        'count': candidate.intervention_count,
        'recent': [
            {'id': action.id, 'action_type': action.action_type, 'action_status': action.action_status, 'result_summary': action.result_summary}
            for action in interventions[:5]
        ],
    }
    recovery_summary = {
        'status': latest_recovery.recovery_status if latest_recovery else None,
        'score': str(latest_recovery.recovery_score) if latest_recovery else None,
        'rationale': latest_recovery.rationale if latest_recovery else '',
    }
    major_blockers = list(dict.fromkeys(candidate.unresolved_blockers))

    final_outcome_summary = (
        f"Disposition {candidate.disposition.disposition_type} ({candidate.disposition.disposition_status}) with "
        f"{len(major_blockers)} unresolved blockers, {len(incidents)} incidents, and {candidate.intervention_count} interventions."
    )
    executive_summary = (
        f"Campaign '{campaign.title}' reached {campaign.status}; closeout is "
        f"{'ready' if candidate.ready_for_closeout else 'pending manual follow-up'} after disposition processing."
    )

    return {
        'executive_summary': executive_summary,
        'lifecycle_summary': lifecycle_summary,
        'major_blockers': major_blockers,
        'incident_summary': incident_summary,
        'intervention_summary': intervention_summary,
        'recovery_summary': recovery_summary,
        'final_outcome_summary': final_outcome_summary,
        'runtime_status': latest_runtime.runtime_status if latest_runtime else None,
    }

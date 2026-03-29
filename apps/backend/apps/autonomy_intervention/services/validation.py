from __future__ import annotations

from apps.autonomy_campaign.models import AutonomyCampaignStatus
from apps.autonomy_intervention.models import InterventionRequestedAction
from apps.autonomy_program.models import ProgramConcurrencyPosture


TERMINAL_STATUSES = {AutonomyCampaignStatus.COMPLETED, AutonomyCampaignStatus.ABORTED, AutonomyCampaignStatus.FAILED}


def validate_intervention(*, campaign, requested_action: str, program_state, critical_incident: bool, has_open_blockers: bool) -> dict:
    blockers: list[str] = []
    requires_approval = requested_action in {
        InterventionRequestedAction.ESCALATE_TO_APPROVAL,
        InterventionRequestedAction.REVIEW_FOR_ABORT,
    }

    if campaign.status in TERMINAL_STATUSES:
        blockers.append('campaign_terminal_state')

    if requested_action == InterventionRequestedAction.PAUSE_CAMPAIGN and campaign.status == AutonomyCampaignStatus.PAUSED:
        blockers.append('campaign_already_paused')

    if requested_action == InterventionRequestedAction.RESUME_CAMPAIGN:
        if campaign.status == AutonomyCampaignStatus.RUNNING:
            blockers.append('campaign_already_running')
        if has_open_blockers:
            blockers.append('campaign_has_open_blockers')

    if requested_action == InterventionRequestedAction.CLEAR_TO_CONTINUE and has_open_blockers:
        blockers.append('unsafe_to_clear_while_blocked')

    if program_state and program_state.concurrency_posture == ProgramConcurrencyPosture.FROZEN:
        if requested_action not in {
            InterventionRequestedAction.PAUSE_CAMPAIGN,
            InterventionRequestedAction.ESCALATE_TO_APPROVAL,
            InterventionRequestedAction.REVIEW_FOR_ABORT,
        }:
            blockers.append('program_posture_frozen')

    if critical_incident and requested_action == InterventionRequestedAction.CLEAR_TO_CONTINUE:
        blockers.append('critical_incident_active')

    return {
        'allowed': len(blockers) == 0,
        'blockers': blockers,
        'requires_approval': requires_approval,
    }

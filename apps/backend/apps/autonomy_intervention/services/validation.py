from __future__ import annotations

from apps.autonomy_campaign.models import AutonomyCampaignStatus
from apps.autonomy_intervention.models import InterventionRequestedAction
from apps.autonomy_program.models import AutonomyProgramState, ProgramConcurrencyPosture


TERMINAL_CAMPAIGN_STATES = {
    AutonomyCampaignStatus.COMPLETED,
    AutonomyCampaignStatus.ABORTED,
    AutonomyCampaignStatus.FAILED,
}


def validate_request(*, campaign, requested_action: str, runtime_snapshot=None) -> tuple[str, list[str]]:
    blockers: list[str] = []
    status = 'READY'

    if campaign.status in TERMINAL_CAMPAIGN_STATES:
        blockers.append('campaign_terminal_state')

    if requested_action == InterventionRequestedAction.PAUSE_CAMPAIGN and campaign.status == AutonomyCampaignStatus.PAUSED:
        blockers.append('campaign_already_paused')

    if requested_action == InterventionRequestedAction.RESUME_CAMPAIGN and campaign.status == AutonomyCampaignStatus.RUNNING:
        blockers.append('campaign_already_running')

    if requested_action == InterventionRequestedAction.RESUME_CAMPAIGN and runtime_snapshot and runtime_snapshot.blockers:
        blockers.append('runtime_blockers_persist')

    latest_program_state = AutonomyProgramState.objects.order_by('-created_at', '-id').first()
    if latest_program_state and latest_program_state.concurrency_posture == ProgramConcurrencyPosture.FROZEN:
        if requested_action in {
            InterventionRequestedAction.RESUME_CAMPAIGN,
            InterventionRequestedAction.CLEAR_TO_CONTINUE,
        }:
            blockers.append('program_frozen_non_conservative_action')

    if runtime_snapshot and runtime_snapshot.incident_impact >= 2 and requested_action == InterventionRequestedAction.CLEAR_TO_CONTINUE:
        blockers.append('critical_incident_pressure')

    if requested_action in {InterventionRequestedAction.REVIEW_FOR_ABORT, InterventionRequestedAction.ESCALATE_TO_APPROVAL}:
        status = 'APPROVAL_REQUIRED'

    if blockers:
        status = 'BLOCKED'
    return status, blockers

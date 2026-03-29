from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.approval_center.models import ApprovalPriority, ApprovalRequest, ApprovalRequestStatus, ApprovalSourceType
from apps.autonomy_campaign.models import AutonomyCampaignStatus
from apps.autonomy_campaign.services import advance_campaign
from apps.autonomy_intervention.models import (
    CampaignInterventionAction,
    InterventionActionStatus,
    InterventionActionType,
    InterventionOutcomeType,
    InterventionRequestStatus,
    InterventionRequestedAction,
)
from apps.autonomy_intervention.services.outcome import blocked_outcome, record_outcome
from apps.autonomy_intervention.services.validation import validate_intervention
from apps.autonomy_program.models import AutonomyProgramState
from apps.incident_commander.models import IncidentRecord


def _action_type_for_request(requested_action: str) -> str:
    return {
        InterventionRequestedAction.PAUSE_CAMPAIGN: InterventionActionType.PAUSE,
        InterventionRequestedAction.RESUME_CAMPAIGN: InterventionActionType.RESUME,
        InterventionRequestedAction.ESCALATE_TO_APPROVAL: InterventionActionType.ESCALATE,
        InterventionRequestedAction.REVIEW_FOR_ABORT: InterventionActionType.ABORT_REVIEW,
        InterventionRequestedAction.CLEAR_TO_CONTINUE: InterventionActionType.CONTINUE_CLEARANCE,
    }[requested_action]


def _open_approval_for_request(request, actor: str):
    return ApprovalRequest.objects.update_or_create(
        source_type=ApprovalSourceType.OTHER,
        source_object_id=f'intervention-request-{request.id}',
        defaults={
            'title': f'Intervention approval for campaign #{request.campaign_id}',
            'summary': request.rationale,
            'priority': ApprovalPriority.HIGH if request.severity in {'HIGH', 'CRITICAL'} else ApprovalPriority.MEDIUM,
            'status': ApprovalRequestStatus.PENDING,
            'requested_at': timezone.now(),
            'metadata': {
                'autonomy_intervention': True,
                'campaign_id': request.campaign_id,
                'requested_action': request.requested_action,
                'requested_by': actor,
            },
        },
    )[0]


@transaction.atomic
def execute_request(*, request, actor: str = 'operator-ui'):
    campaign = request.campaign
    before = campaign.status
    action = CampaignInterventionAction.objects.create(
        campaign=campaign,
        intervention_request=request,
        action_type=_action_type_for_request(request.requested_action),
        action_status=InterventionActionStatus.EXECUTING,
        executed_by=actor,
        reason_codes=request.reason_codes,
        blockers=request.blockers,
        metadata={'source_type': request.source_type},
    )

    latest_program = AutonomyProgramState.objects.order_by('-created_at', '-id').first()
    critical_incident = IncidentRecord.objects.filter(status__in=['OPEN', 'DEGRADED', 'ESCALATED'], severity='critical').exists()
    has_open_blockers = campaign.checkpoints.filter(status='OPEN').exists()
    validation = validate_intervention(
        campaign=campaign,
        requested_action=request.requested_action,
        program_state=latest_program,
        critical_incident=critical_incident,
        has_open_blockers=has_open_blockers,
    )
    if not validation['allowed']:
        action.action_status = InterventionActionStatus.BLOCKED
        action.blockers = validation['blockers']
        action.failure_message = 'Intervention blocked by policy or campaign safety checks.'
        action.save(update_fields=['action_status', 'blockers', 'failure_message', 'updated_at'])
        request.request_status = InterventionRequestStatus.BLOCKED
        request.blockers = validation['blockers']
        request.save(update_fields=['request_status', 'blockers', 'updated_at'])
        blocked_outcome(action, before, 'Intervention blocked by validation rules.', validation['blockers'])
        return action

    try:
        if request.requested_action == InterventionRequestedAction.PAUSE_CAMPAIGN:
            campaign.status = AutonomyCampaignStatus.PAUSED
            campaign.metadata = {**(campaign.metadata or {}), 'paused_by_intervention': actor}
            campaign.save(update_fields=['status', 'metadata', 'updated_at'])
            outcome_type = InterventionOutcomeType.CAMPAIGN_PAUSED
            summary = f'Campaign #{campaign.id} paused by {actor}.'
        elif request.requested_action == InterventionRequestedAction.RESUME_CAMPAIGN:
            campaign = advance_campaign(campaign=campaign, actor=actor)
            outcome_type = InterventionOutcomeType.CAMPAIGN_RESUMED if campaign.status != before else InterventionOutcomeType.NO_STATE_CHANGE
            summary = f'Campaign #{campaign.id} resumed/advanced by {actor}.'
        elif request.requested_action in {InterventionRequestedAction.ESCALATE_TO_APPROVAL, InterventionRequestedAction.REVIEW_FOR_ABORT}:
            approval = _open_approval_for_request(request, actor)
            request.approval_request = approval
            request.request_status = InterventionRequestStatus.APPROVAL_REQUIRED
            request.save(update_fields=['approval_request', 'request_status', 'updated_at'])
            outcome_type = InterventionOutcomeType.ABORT_REVIEW_OPENED if request.requested_action == InterventionRequestedAction.REVIEW_FOR_ABORT else InterventionOutcomeType.APPROVAL_OPENED
            summary = f'Approval request #{approval.id} opened for intervention #{request.id}.'
        else:
            outcome_type = InterventionOutcomeType.CONTINUE_CONFIRMED
            summary = f'Campaign #{campaign.id} manually cleared to continue by {actor}.'

        after = campaign.status
        action.action_status = InterventionActionStatus.EXECUTED
        action.result_summary = summary
        action.executed_at = timezone.now()
        action.save(update_fields=['action_status', 'result_summary', 'executed_at', 'updated_at'])
        request.request_status = InterventionRequestStatus.EXECUTED if request.requested_action not in {InterventionRequestedAction.ESCALATE_TO_APPROVAL, InterventionRequestedAction.REVIEW_FOR_ABORT} else request.request_status
        request.save(update_fields=['request_status', 'updated_at'])
        record_outcome(action=action, outcome_type=outcome_type, campaign_state_before=before, campaign_state_after=after, summary=summary)
        return action
    except Exception as exc:  # noqa: BLE001
        action.action_status = InterventionActionStatus.FAILED
        action.failure_message = str(exc)
        action.save(update_fields=['action_status', 'failure_message', 'updated_at'])
        request.request_status = InterventionRequestStatus.REJECTED
        request.save(update_fields=['request_status', 'updated_at'])
        record_outcome(
            action=action,
            outcome_type=InterventionOutcomeType.ACTION_FAILED,
            campaign_state_before=before,
            campaign_state_after=campaign.status,
            summary=f'Intervention failed: {exc}',
        )
        return action

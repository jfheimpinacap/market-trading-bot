from __future__ import annotations

from django.db import transaction

from apps.autonomy_campaign.models import (
    AutonomyCampaign,
    AutonomyCampaignActionType,
    AutonomyCampaignCheckpointStatus,
    AutonomyCampaignStatus,
    AutonomyCampaignStep,
    AutonomyCampaignStepStatus,
    AutonomyCampaignCheckpointType,
)
from apps.autonomy_campaign.services.checkpoints import create_approval_checkpoint, create_checkpoint, sync_open_checkpoints
from apps.autonomy_manager.models import AutonomyStageState, AutonomyStageTransition, AutonomyTransitionStatus
from apps.autonomy_manager.services.transitions import apply_transition, resolve_transition_readiness
from apps.autonomy_rollout.models import AutonomyRolloutStatus
from apps.autonomy_rollout.services import create_rollout_run


@transaction.atomic
def start_campaign(*, campaign: AutonomyCampaign, actor: str = 'operator-ui') -> AutonomyCampaign:
    if campaign.status not in {AutonomyCampaignStatus.READY, AutonomyCampaignStatus.PAUSED, AutonomyCampaignStatus.BLOCKED}:
        return campaign
    campaign.status = AutonomyCampaignStatus.RUNNING
    campaign.metadata = {**(campaign.metadata or {}), 'started_by': actor}
    campaign.save(update_fields=['status', 'metadata', 'updated_at'])
    return advance_campaign(campaign=campaign, actor=actor)


def _ensure_transition(step: AutonomyCampaignStep) -> AutonomyStageTransition:
    transition_id = (step.metadata or {}).get('autonomy_transition_id')
    if transition_id:
        return AutonomyStageTransition.objects.select_related('approval_request', 'state', 'domain').get(pk=transition_id)

    if not step.domain_id:
        raise ValueError('Apply transition step requires domain.')
    state = AutonomyStageState.objects.get(domain=step.domain)
    requested_stage = (step.metadata or {}).get('requested_stage') or state.current_stage
    transition = AutonomyStageTransition.objects.create(
        domain=step.domain,
        state=state,
        previous_stage=state.current_stage,
        requested_stage=requested_stage,
        rationale=step.rationale,
        reason_codes=['AUTONOMY_CAMPAIGN'],
        evidence_refs=[{'type': 'autonomy_campaign', 'id': step.campaign_id}],
        status=AutonomyTransitionStatus.READY_TO_APPLY,
        metadata={
            'created_by_campaign': True,
            'campaign_id': step.campaign_id,
            'campaign_step_id': step.id,
        },
    )
    step.metadata = {**(step.metadata or {}), 'autonomy_transition_id': transition.id}
    step.save(update_fields=['metadata', 'updated_at'])
    return transition


def _step_blocked_by_open_checkpoint(step: AutonomyCampaignStep) -> bool:
    return step.checkpoints.filter(status=AutonomyCampaignCheckpointStatus.OPEN).exists()


@transaction.atomic
def advance_campaign(*, campaign: AutonomyCampaign, actor: str = 'operator-ui') -> AutonomyCampaign:
    sync_open_checkpoints(campaign.id)

    if campaign.status not in {AutonomyCampaignStatus.RUNNING, AutonomyCampaignStatus.BLOCKED, AutonomyCampaignStatus.PAUSED}:
        return campaign

    runnable = campaign.steps.filter(status__in=[AutonomyCampaignStepStatus.PENDING, AutonomyCampaignStepStatus.READY, AutonomyCampaignStepStatus.WAITING_APPROVAL, AutonomyCampaignStepStatus.OBSERVING]).order_by('step_order')
    for step in runnable:
        if _step_blocked_by_open_checkpoint(step):
            step.status = AutonomyCampaignStepStatus.WAITING_APPROVAL
            step.save(update_fields=['status', 'updated_at'])
            campaign.status = AutonomyCampaignStatus.BLOCKED
            campaign.save(update_fields=['status', 'updated_at'])
            return campaign

        if step.action_type == AutonomyCampaignActionType.APPLY_TRANSITION:
            if (step.metadata or {}).get('require_approval') and not step.checkpoints.filter(
                checkpoint_type=AutonomyCampaignCheckpointType.APPROVAL_REQUIRED,
                status=AutonomyCampaignCheckpointStatus.OPEN,
            ).exists():
                create_approval_checkpoint(
                    step=step,
                    summary=f'Manual approval required by campaign policy before domain transition for {step.domain.slug if step.domain_id else \"n/a\"}.',
                    metadata={'domain': step.domain.slug if step.domain_id else None},
                )
                step.status = AutonomyCampaignStepStatus.WAITING_APPROVAL
                step.save(update_fields=['status', 'updated_at'])
                campaign.status = AutonomyCampaignStatus.BLOCKED
                campaign.blocked_steps = campaign.steps.filter(status=AutonomyCampaignStepStatus.WAITING_APPROVAL).count()
                campaign.save(update_fields=['status', 'blocked_steps', 'updated_at'])
                return campaign
            transition = _ensure_transition(step)
            transition = resolve_transition_readiness(transition)
            if transition.approval_request_id and transition.approval_request.status != 'APPROVED':
                if not step.checkpoints.filter(checkpoint_type=AutonomyCampaignCheckpointType.APPROVAL_REQUIRED, status=AutonomyCampaignCheckpointStatus.OPEN).exists():
                    create_approval_checkpoint(
                        step=step,
                        summary=f'Approval required before applying {transition.domain.slug} transition to {transition.requested_stage}.',
                        metadata={'autonomy_transition_id': transition.id, 'domain': transition.domain.slug},
                    )
                step.status = AutonomyCampaignStepStatus.WAITING_APPROVAL
                step.save(update_fields=['status', 'updated_at'])
                campaign.status = AutonomyCampaignStatus.BLOCKED
                campaign.blocked_steps = campaign.steps.filter(status=AutonomyCampaignStepStatus.WAITING_APPROVAL).count()
                campaign.save(update_fields=['status', 'blocked_steps', 'updated_at'])
                return campaign
            apply_transition(transition=transition, applied_by=actor)
            step.status = AutonomyCampaignStepStatus.DONE
            step.metadata = {**(step.metadata or {}), 'autonomy_transition_id': transition.id}
            step.save(update_fields=['status', 'metadata', 'updated_at'])

        elif step.action_type == AutonomyCampaignActionType.START_ROLLOUT:
            transition_id = (step.metadata or {}).get('autonomy_transition_id')
            transition = AutonomyStageTransition.objects.filter(pk=transition_id).first()
            if not transition or transition.status != AutonomyTransitionStatus.APPLIED:
                step.status = AutonomyCampaignStepStatus.FAILED
                step.save(update_fields=['status', 'updated_at'])
                campaign.status = AutonomyCampaignStatus.FAILED
                campaign.save(update_fields=['status', 'updated_at'])
                return campaign
            run = create_rollout_run(transition=transition)
            step.status = AutonomyCampaignStepStatus.DONE
            step.metadata = {**(step.metadata or {}), 'autonomy_rollout_run_id': run.id}
            step.save(update_fields=['status', 'metadata', 'updated_at'])

        elif step.action_type == AutonomyCampaignActionType.EVALUATE_ROLLOUT:
            run_id = (step.metadata or {}).get('autonomy_rollout_run_id')
            run = campaign.steps.filter(action_type=AutonomyCampaignActionType.START_ROLLOUT, domain=step.domain).order_by('-step_order').first()
            run_id = run_id or ((run.metadata or {}).get('autonomy_rollout_run_id') if run else None)
            if not run_id:
                step.status = AutonomyCampaignStepStatus.FAILED
                step.save(update_fields=['status', 'updated_at'])
                continue
            from apps.autonomy_rollout.models import AutonomyRolloutRun

            rollout = AutonomyRolloutRun.objects.get(pk=run_id)
            if rollout.rollout_status in {AutonomyRolloutStatus.OBSERVING, AutonomyRolloutStatus.CAUTION}:
                if not step.checkpoints.filter(checkpoint_type=AutonomyCampaignCheckpointType.ROLLOUT_OBSERVATION, status=AutonomyCampaignCheckpointStatus.OPEN).exists():
                    create_checkpoint(
                        step=step,
                        checkpoint_type=AutonomyCampaignCheckpointType.ROLLOUT_OBSERVATION,
                        summary=f'Waiting rollout evaluation for domain {rollout.domain.slug}.',
                        metadata={'autonomy_rollout_run_id': rollout.id},
                    )
                step.status = AutonomyCampaignStepStatus.OBSERVING
                step.metadata = {**(step.metadata or {}), 'autonomy_rollout_run_id': rollout.id}
                step.save(update_fields=['status', 'metadata', 'updated_at'])
                campaign.status = AutonomyCampaignStatus.BLOCKED
                campaign.save(update_fields=['status', 'updated_at'])
                return campaign
            if rollout.rollout_status in {AutonomyRolloutStatus.ROLLBACK_RECOMMENDED, AutonomyRolloutStatus.FREEZE_RECOMMENDED, AutonomyRolloutStatus.ABORTED}:
                step.status = AutonomyCampaignStepStatus.FAILED
                step.save(update_fields=['status', 'updated_at'])
                campaign.status = AutonomyCampaignStatus.BLOCKED
                campaign.save(update_fields=['status', 'updated_at'])
                return campaign
            step.status = AutonomyCampaignStepStatus.DONE
            step.save(update_fields=['status', 'updated_at'])

    campaign.completed_steps = campaign.steps.filter(status=AutonomyCampaignStepStatus.DONE).count()
    campaign.blocked_steps = campaign.steps.filter(status__in=[AutonomyCampaignStepStatus.WAITING_APPROVAL, AutonomyCampaignStepStatus.OBSERVING]).count()
    if campaign.completed_steps >= campaign.total_steps and campaign.total_steps > 0:
        campaign.status = AutonomyCampaignStatus.COMPLETED
    elif campaign.blocked_steps > 0:
        campaign.status = AutonomyCampaignStatus.BLOCKED
    else:
        campaign.status = AutonomyCampaignStatus.RUNNING
    campaign.current_wave = campaign.steps.filter(status__in=[AutonomyCampaignStepStatus.PENDING, AutonomyCampaignStepStatus.READY, AutonomyCampaignStepStatus.WAITING_APPROVAL, AutonomyCampaignStepStatus.OBSERVING]).order_by('wave', 'step_order').values_list('wave', flat=True).first() or campaign.current_wave
    campaign.save(update_fields=['completed_steps', 'blocked_steps', 'status', 'current_wave', 'updated_at'])
    return campaign


@transaction.atomic
def abort_campaign(*, campaign: AutonomyCampaign, reason: str = '', actor: str = 'operator-ui') -> AutonomyCampaign:
    campaign.status = AutonomyCampaignStatus.ABORTED
    campaign.metadata = {**(campaign.metadata or {}), 'aborted_by': actor, 'abort_reason': reason}
    campaign.save(update_fields=['status', 'metadata', 'updated_at'])
    campaign.steps.filter(status__in=[AutonomyCampaignStepStatus.PENDING, AutonomyCampaignStepStatus.READY, AutonomyCampaignStepStatus.WAITING_APPROVAL, AutonomyCampaignStepStatus.OBSERVING]).update(status=AutonomyCampaignStepStatus.ABORTED)
    return campaign

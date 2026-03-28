from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.approval_center.models import ApprovalPriority, ApprovalRequest, ApprovalRequestStatus, ApprovalSourceType
from apps.autonomy_manager.services.transitions import rollback_transition
from apps.autonomy_rollout.models import AutonomyRolloutRun, AutonomyRolloutStatus


@transaction.atomic
def apply_manual_rollback(*, run: AutonomyRolloutRun, reason: str, require_approval: bool = True) -> dict:
    if run.rollout_status == AutonomyRolloutStatus.ABORTED:
        raise ValueError('Cannot rollback an aborted rollout run.')

    transition = run.autonomy_stage_transition
    if transition.status != 'APPLIED':
        raise ValueError('Only applied autonomy transitions can be rolled back from rollout monitor.')

    approval_request = None
    if require_approval:
        approval_request, _ = ApprovalRequest.objects.get_or_create(
            source_type=ApprovalSourceType.OTHER,
            source_object_id=f'autonomy_rollout_rollback:{run.id}',
            defaults={
                'title': f'Rollback autonomy stage for domain {run.domain.slug}',
                'summary': reason,
                'priority': ApprovalPriority.HIGH,
                'status': ApprovalRequestStatus.PENDING,
                'requested_at': timezone.now(),
                'metadata': {
                    'autonomy_rollout_run_id': run.id,
                    'autonomy_transition_id': transition.id,
                    'domain': run.domain.slug,
                    'trace': {'root_type': 'autonomy_rollout_run', 'root_id': str(run.id)},
                },
            },
        )

    before = {'transition_status': transition.status, 'stage': transition.applied_stage}
    updated_transition = rollback_transition(transition=transition, rolled_back_by='autonomy-rollout-monitor')
    after = {'transition_status': updated_transition.status, 'stage': updated_transition.state.current_stage}

    run.rollout_status = AutonomyRolloutStatus.ABORTED
    run.summary = 'Manual rollback applied to restore previous autonomy stage.'
    run.metadata = {
        **(run.metadata or {}),
        'rollback': {
            'reason': reason,
            'applied_at': timezone.now().isoformat(),
            'approval_request_id': approval_request.id if approval_request else None,
            'before': before,
            'after': after,
        },
    }
    run.save(update_fields=['rollout_status', 'summary', 'metadata', 'updated_at'])
    return {
        'run_id': run.id,
        'approval_request_id': approval_request.id if approval_request else None,
        'before': before,
        'after': after,
        'transition_id': updated_transition.id,
    }

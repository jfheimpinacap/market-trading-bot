from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.approval_center.models import ApprovalPriority, ApprovalRequest, ApprovalRequestStatus, ApprovalSourceType
from apps.automation_policy.models import AutomationPolicyRule
from apps.policy_rollout.models import PolicyRolloutRun, PolicyRolloutStatus


@transaction.atomic
def apply_manual_rollback(*, run: PolicyRolloutRun, reason: str, require_approval: bool = True) -> dict:
    if run.rollout_status == PolicyRolloutStatus.ABORTED:
        raise ValueError('Cannot rollback an aborted rollout run.')

    candidate = run.policy_tuning_candidate
    log = run.application_log

    approval_request = None
    if require_approval:
        approval_request, _ = ApprovalRequest.objects.get_or_create(
            source_type=ApprovalSourceType.OTHER,
            source_object_id=f'policy_rollout_rollback:{run.id}',
            defaults={
                'title': f'Rollback policy tuning candidate #{candidate.id}',
                'summary': reason,
                'priority': ApprovalPriority.HIGH,
                'status': ApprovalRequestStatus.PENDING,
                'requested_at': timezone.now(),
                'metadata': {
                    'policy_rollout_run_id': run.id,
                    'policy_tuning_candidate_id': candidate.id,
                    'trace': {'root_type': 'policy_rollout_run', 'root_id': str(run.id)},
                },
            },
        )

    rule = candidate.current_rule
    if rule:
        before = {'trust_tier': rule.trust_tier, 'conditions': rule.conditions}
        rule.trust_tier = log.before_snapshot.get('trust_tier') or rule.trust_tier
        rule.conditions = log.before_snapshot.get('conditions') or rule.conditions
        rule.save(update_fields=['trust_tier', 'conditions', 'updated_at'])
        after = {'trust_tier': rule.trust_tier, 'conditions': rule.conditions}
    else:
        before = {}
        after = {}

    candidate.status = 'SUPERSEDED'
    candidate.metadata = {
        **(candidate.metadata or {}),
        'rolled_back': True,
        'rolled_back_at': timezone.now().isoformat(),
        'rollback_reason': reason,
    }
    candidate.save(update_fields=['status', 'metadata', 'updated_at'])

    run.rollout_status = PolicyRolloutStatus.ABORTED
    run.summary = 'Manual rollback applied to restore pre-change policy state.'
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
    }

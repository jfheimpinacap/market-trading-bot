from django.db.models import Count

from apps.go_live_gate.models import GoLiveApprovalRequest, GoLiveApprovalStatus, GoLiveChecklistRun, GoLiveGateStateCode, GoLiveRehearsalRun
from apps.go_live_gate.services.firewall import evaluate_firewall


def build_go_live_state() -> dict:
    firewall = evaluate_firewall()
    latest_checklist = GoLiveChecklistRun.objects.order_by('-created_at', '-id').first()
    latest_approval = GoLiveApprovalRequest.objects.order_by('-created_at', '-id').first()

    blockers: list[str] = []
    state = GoLiveGateStateCode.PAPER_ONLY_LOCKED

    if firewall['blocked_by_firewall']:
        blockers.append('Capital firewall blocks any live transition by policy.')
        state = GoLiveGateStateCode.LIVE_DISABLED_BY_POLICY

    if latest_checklist and latest_checklist.failed_items:
        blockers.extend(latest_checklist.blocking_reasons)
        state = GoLiveGateStateCode.REMEDIATION_REQUIRED
    elif latest_checklist and latest_checklist.passed:
        state = GoLiveGateStateCode.PRELIVE_REHEARSAL_READY

    if latest_approval and latest_approval.status in {GoLiveApprovalStatus.DRAFT, GoLiveApprovalStatus.PENDING}:
        state = GoLiveGateStateCode.MANUAL_APPROVAL_PENDING
        blockers.append('Manual approval request is still pending.')

    return {
        'state': state,
        'blockers': blockers,
        'firewall': firewall,
        'latest_checklist_run_id': latest_checklist.id if latest_checklist else None,
        'latest_approval_request_id': latest_approval.id if latest_approval else None,
        'paper_only': True,
    }


def build_go_live_summary() -> dict:
    checklist_counts = {row['passed']: row['count'] for row in GoLiveChecklistRun.objects.values('passed').annotate(count=Count('id'))}
    approval_counts = {row['status']: row['count'] for row in GoLiveApprovalRequest.objects.values('status').annotate(count=Count('id'))}
    rehearsal_counts = {
        'total': GoLiveRehearsalRun.objects.count(),
        'allowed_in_rehearsal': GoLiveRehearsalRun.objects.filter(allowed_to_proceed_in_rehearsal=True).count(),
        'blocked_by_firewall': GoLiveRehearsalRun.objects.filter(blocked_by_firewall=True).count(),
    }
    return {
        'gate': build_go_live_state(),
        'checklists': {
            'total': GoLiveChecklistRun.objects.count(),
            'passed': checklist_counts.get(True, 0),
            'failed': checklist_counts.get(False, 0),
        },
        'approvals': {
            'total': GoLiveApprovalRequest.objects.count(),
            'status_counts': approval_counts,
        },
        'rehearsals': rehearsal_counts,
    }

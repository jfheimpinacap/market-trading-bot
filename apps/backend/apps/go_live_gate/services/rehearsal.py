from django.db import transaction

from apps.broker_bridge.models import BrokerOrderIntent
from apps.broker_bridge.services.dry_run import run_dry_run
from apps.operator_queue.models import OperatorQueueItem, OperatorQueuePriority, OperatorQueueSource, OperatorQueueType
from apps.go_live_gate.models import GoLiveApprovalRequest, GoLiveApprovalStatus, GoLiveChecklistRun, GoLiveGateStateCode, GoLiveRehearsalRun
from apps.go_live_gate.services.firewall import evaluate_firewall
from apps.go_live_gate.services.state import build_go_live_state


@transaction.atomic
def run_rehearsal(intent: BrokerOrderIntent, requested_by: str = 'local-operator', metadata: dict | None = None) -> GoLiveRehearsalRun:
    metadata = metadata or {}
    latest_checklist = GoLiveChecklistRun.objects.order_by('-created_at', '-id').first()
    latest_approved_request = GoLiveApprovalRequest.objects.filter(status=GoLiveApprovalStatus.APPROVED).order_by('-created_at', '-id').first()
    pending_requests = GoLiveApprovalRequest.objects.filter(status__in=[GoLiveApprovalStatus.DRAFT, GoLiveApprovalStatus.PENDING]).order_by('-created_at', '-id')

    firewall = evaluate_firewall()
    gate = build_go_live_state()

    missing_preconditions: list[str] = []
    missing_approvals: list[str] = []
    blocked_reasons: list[str] = []

    if not latest_checklist or not latest_checklist.passed:
        missing_preconditions.append('prelive_checklist_not_passed')
    if not latest_approved_request:
        missing_approvals.append('approved_manual_request_missing')
    if pending_requests.exists():
        missing_approvals.append('manual_request_pending')

    blocked_by_firewall = firewall['blocked_by_firewall']
    if blocked_by_firewall:
        blocked_reasons.append('capital_firewall_blocks_live_transition')

    if missing_preconditions:
        blocked_reasons.append('preconditions_missing')
    if missing_approvals:
        blocked_reasons.append('approvals_missing')

    dry_run = run_dry_run(intent=intent, metadata={'triggered_from': 'go_live_rehearsal', 'requested_by': requested_by, **metadata})
    allowed_in_rehearsal = not missing_preconditions and not missing_approvals

    run = GoLiveRehearsalRun.objects.create(
        intent=intent,
        checklist_run=latest_checklist,
        approval_request=latest_approved_request,
        gate_state=gate['state'] if gate['state'] else GoLiveGateStateCode.PAPER_ONLY_LOCKED,
        allowed_to_proceed_in_rehearsal=allowed_in_rehearsal,
        blocked_by_firewall=blocked_by_firewall,
        missing_approvals=missing_approvals,
        missing_preconditions=missing_preconditions,
        blocked_reasons=blocked_reasons,
        final_dry_run_disposition=dry_run.simulated_response,
        dry_run_reference_id=dry_run.id,
        metadata={'requested_by': requested_by, **metadata},
    )

    if blocked_reasons:
        OperatorQueueItem.objects.create(
            source=OperatorQueueSource.SAFETY,
            queue_type=OperatorQueueType.BLOCKED_REVIEW,
            priority=OperatorQueuePriority.HIGH,
            headline='Go-live rehearsal blocked',
            summary='Final rehearsal remained in paper-only mode and was blocked by checklist/approval/firewall conditions.',
            rationale='; '.join(blocked_reasons),
            metadata={
                'go_live_rehearsal_run_id': run.id,
                'intent_id': intent.id,
                'missing_preconditions': missing_preconditions,
                'missing_approvals': missing_approvals,
                'firewall_blocked': blocked_by_firewall,
            },
        )

    return run

from apps.approval_center.models import ApprovalRequest, ApprovalSourceType


def get_approval_impact_preview(approval: ApprovalRequest) -> dict:
    if approval.source_type == ApprovalSourceType.RUNBOOK_CHECKPOINT:
        step_title = approval.metadata.get('runbook_step_title') or 'requested step'
        return {
            'approve': f'Approving resumes supervised runbook autopilot at step: {step_title}.',
            'reject': 'Rejecting keeps the runbook autopilot blocked and requires manual remediation.',
            'expire': 'Expiring leaves the checkpoint unresolved and keeps the runbook paused.',
            'escalate': 'Escalating flags this checkpoint for manual incident/mission-control review.',
            'evidence': [
                'Runbook checkpoint reason',
                'Blocking constraints from automation policy',
                'Context snapshot captured at pause time',
            ],
        }

    if approval.source_type == ApprovalSourceType.GO_LIVE_REQUEST:
        return {
            'approve': 'Approving advances pre-live rehearsal gating only; it does NOT enable live trading in this phase.',
            'reject': 'Rejecting keeps go-live transition blocked and remediation/manual checks in control.',
            'expire': 'Expiring requires a fresh go-live approval request before proceeding.',
            'escalate': 'Escalating asks for additional operator review before rehearsal continuation.',
            'evidence': ['Checklist run status', 'Blocking reasons', 'Requested mode and scope'],
        }

    if approval.source_type == ApprovalSourceType.OPERATOR_QUEUE_ITEM:
        return {
            'approve': 'Approving resolves this approval-required queue item and may execute a paper-only action.',
            'reject': 'Rejecting keeps execution blocked and records explicit operator rationale.',
            'expire': 'Expiring marks the queue item stale so it does not trigger accidental action.',
            'escalate': 'Escalating surfaces this item for deeper investigation/remediation runbooks.',
            'evidence': ['Queue headline + rationale', 'Suggested action/quantity', 'Related market/proposal links'],
        }

    return {
        'approve': 'Approving marks this request as approved and unlocks dependent manual-first workflow steps.',
        'reject': 'Rejecting leaves the dependent workflow blocked pending further operator intervention.',
        'expire': 'Expiring archives this request and requires a new request to continue.',
        'escalate': 'Escalating marks this request as needing higher-priority manual review.',
        'evidence': ['Request metadata and source context'],
    }

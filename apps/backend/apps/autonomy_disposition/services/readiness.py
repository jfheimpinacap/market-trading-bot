from __future__ import annotations

from apps.autonomy_disposition.models import DispositionReadiness


def evaluate_disposition_readiness(context):
    campaign = context.campaign
    blockers: list[str] = []
    reason_codes: list[str] = []

    if context.pending_approvals_count > 0:
        blockers.append('pending_approval_requests')
        reason_codes.append('approval_pending')
    if context.pending_checkpoints_count > 0:
        blockers.append('open_checkpoints')
        reason_codes.append('checkpoint_pending')
    if context.unresolved_incident_pressure > 0:
        blockers.append('unresolved_incident_pressure')
        reason_codes.append('incident_pressure')

    recovery_status = context.recovery_snapshot.recovery_status if context.recovery_snapshot else None
    if recovery_status == 'REVIEW_ABORT':
        readiness = DispositionReadiness.READY_TO_ABORT
        reason_codes.append('recovery_review_abort')
    elif recovery_status == 'CLOSE_CANDIDATE':
        readiness = DispositionReadiness.READY_TO_CLOSE
        reason_codes.append('recovery_close_candidate')
    elif campaign.status == 'ABORTED':
        readiness = DispositionReadiness.READY_TO_ABORT
        reason_codes.append('campaign_aborted')
    elif campaign.status == 'COMPLETED' and not blockers:
        readiness = DispositionReadiness.READY_TO_CLOSE
        reason_codes.append('campaign_completed_clean')
    elif campaign.status == 'FAILED':
        readiness = DispositionReadiness.READY_TO_RETIRE
        reason_codes.append('campaign_failed_retire')
    elif campaign.metadata.get('retire_requested'):
        readiness = DispositionReadiness.READY_TO_RETIRE
        reason_codes.append('program_retire_requested')
    elif blockers:
        readiness = DispositionReadiness.REQUIRE_MORE_REVIEW
    else:
        readiness = DispositionReadiness.KEEP_OPEN

    risk_level = 'LOW'
    if context.unresolved_incident_pressure > 0 or campaign.status in {'FAILED', 'BLOCKED'}:
        risk_level = 'HIGH'
    elif blockers or campaign.status in {'PAUSED', 'RUNNING'}:
        risk_level = 'MEDIUM'

    rationale = f"Disposition readiness={readiness} derived from status={campaign.status} with blockers={', '.join(blockers) if blockers else 'none'}."
    return {
        'disposition_readiness': readiness,
        'closure_risk_level': risk_level,
        'blockers': blockers,
        'reason_codes': reason_codes,
        'rationale': rationale,
    }

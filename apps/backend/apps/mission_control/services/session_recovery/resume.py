from __future__ import annotations

from apps.mission_control.models import (
    AutonomousRecoveryBlocker,
    AutonomousResumeDecision,
    AutonomousResumeDecisionStatus,
    AutonomousResumeDecisionType,
    AutonomousSessionRecoverySnapshot,
)


def derive_resume_decision(*, snapshot: AutonomousSessionRecoverySnapshot, blockers: list[AutonomousRecoveryBlocker]) -> AutonomousResumeDecision:
    blocker_types = {blocker.blocker_type for blocker in blockers}
    reason_codes = list(dict.fromkeys(snapshot.reason_codes + [code for blocker in blockers for code in (blocker.reason_codes or [])]))

    decision_type = AutonomousResumeDecisionType.KEEP_PAUSED
    decision_status = AutonomousResumeDecisionStatus.PROPOSED

    if 'SAFETY_BLOCK_ACTIVE' in blocker_types or 'RUNTIME_BLOCK_ACTIVE' in blocker_types:
        decision_type = AutonomousResumeDecisionType.STOP_SESSION_PERMANENTLY if snapshot.recovery_status == 'UNRECOVERABLE' else AutonomousResumeDecisionType.KEEP_PAUSED
    elif 'INCIDENT_PRESSURE_ACTIVE' in blocker_types:
        decision_type = AutonomousResumeDecisionType.ESCALATE_TO_INCIDENT_REVIEW
        decision_status = AutonomousResumeDecisionStatus.BLOCKED
    elif snapshot.recovery_status == 'UNRECOVERABLE':
        decision_type = AutonomousResumeDecisionType.STOP_SESSION_PERMANENTLY
        decision_status = AutonomousResumeDecisionStatus.BLOCKED
    elif 'RECENT_FAILURE_STREAK' in blocker_types or 'RECENT_BLOCKED_STREAK' in blocker_types or 'MANUAL_REVIEW_REQUIRED' in blocker_types:
        decision_type = AutonomousResumeDecisionType.REQUIRE_MANUAL_RECOVERY_REVIEW
        decision_status = AutonomousResumeDecisionStatus.BLOCKED
    elif snapshot.recovery_status in {'PARTIALLY_RECOVERED', 'STABILIZING'} or 'COOLDOWN_ACTIVE' in blocker_types:
        decision_type = AutonomousResumeDecisionType.RESUME_IN_MONITOR_ONLY_MODE
    elif snapshot.recovery_status == 'RECOVERED' and not blockers:
        decision_type = AutonomousResumeDecisionType.READY_TO_RESUME
    else:
        decision_type = AutonomousResumeDecisionType.KEEP_PAUSED

    summary = f'resume_decision={decision_type} blockers={len(blockers)} recovery_status={snapshot.recovery_status}'
    return AutonomousResumeDecision.objects.create(
        linked_session=snapshot.linked_session,
        linked_recovery_snapshot=snapshot,
        decision_type=decision_type,
        decision_status=decision_status,
        auto_applicable=False,
        decision_summary=summary,
        reason_codes=reason_codes,
        metadata={'blocker_types': sorted(blocker_types)},
    )

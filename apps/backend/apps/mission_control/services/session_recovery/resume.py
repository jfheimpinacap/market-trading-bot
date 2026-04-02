from __future__ import annotations

from apps.mission_control.models import (
    AutonomousRecoveryBlocker,
    AutonomousResumeDecision,
    AutonomousResumeDecisionStatus,
    AutonomousResumeDecisionType,
    AutonomousSessionRecoverySnapshot,
)
from apps.runtime_governor.mode_enforcement.services.enforcement import get_module_enforcement_state


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

    recovery_enforcement = get_module_enforcement_state(module_name='session_recovery')
    recovery_impact = (recovery_enforcement.get('impact') or {}).get('impact_status')
    if recovery_impact == 'REDUCED':
        decision_type = AutonomousResumeDecisionType.REQUIRE_MANUAL_RECOVERY_REVIEW
        decision_status = AutonomousResumeDecisionStatus.BLOCKED
        reason_codes.append('global_mode_enforcement_manual_recovery_review')
    elif recovery_impact == 'THROTTLED':
        decision_type = AutonomousResumeDecisionType.RESUME_IN_MONITOR_ONLY_MODE
        reason_codes.append('global_mode_enforcement_throttle_recovery')
    elif recovery_impact == 'MONITOR_ONLY':
        decision_type = AutonomousResumeDecisionType.RESUME_IN_MONITOR_ONLY_MODE
        decision_status = AutonomousResumeDecisionStatus.PROPOSED
        reason_codes.append('global_mode_enforcement_monitor_only_recovery')
    elif recovery_impact == 'BLOCKED':
        decision_type = AutonomousResumeDecisionType.KEEP_PAUSED
        decision_status = AutonomousResumeDecisionStatus.BLOCKED
        reason_codes.append('global_mode_enforcement_block_recovery')

    summary = f'resume_decision={decision_type} blockers={len(blockers)} recovery_status={snapshot.recovery_status}'
    return AutonomousResumeDecision.objects.create(
        linked_session=snapshot.linked_session,
        linked_recovery_snapshot=snapshot,
        decision_type=decision_type,
        decision_status=decision_status,
        auto_applicable=False,
        decision_summary=summary,
        reason_codes=reason_codes,
        metadata={'blocker_types': sorted(blocker_types), 'mode_enforcement': recovery_enforcement},
    )

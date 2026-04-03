from __future__ import annotations

from apps.mission_control.models import (
    GovernanceBacklogPressureDecision,
    GovernanceBacklogPressureDecisionStatus,
    GovernanceBacklogPressureDecisionType,
    GovernanceBacklogPressureSnapshot,
    GovernanceBacklogPressureState,
)


def build_backlog_pressure_decision(snapshot: GovernanceBacklogPressureSnapshot) -> GovernanceBacklogPressureDecision:
    decision_type = GovernanceBacklogPressureDecisionType.KEEP_BACKLOG_PRESSURE_NORMAL
    decision_status = GovernanceBacklogPressureDecisionStatus.APPLIED
    summary = 'Backlog pressure is normal; keep runtime posture unchanged.'

    if snapshot.pressure_state == GovernanceBacklogPressureState.CAUTION:
        decision_type = GovernanceBacklogPressureDecisionType.ELEVATE_RUNTIME_CAUTION_SIGNAL
        summary = 'Backlog pressure is caution; elevate conservative runtime caution signal.'
    elif snapshot.pressure_state == GovernanceBacklogPressureState.HIGH:
        decision_type = GovernanceBacklogPressureDecisionType.ELEVATE_MONITOR_ONLY_BIAS
        summary = 'Backlog pressure is high; increase monitor-only bias for runtime posture.'
    elif snapshot.pressure_state == GovernanceBacklogPressureState.CRITICAL:
        decision_type = GovernanceBacklogPressureDecisionType.REQUIRE_MANUAL_BACKLOG_REVIEW
        decision_status = GovernanceBacklogPressureDecisionStatus.BLOCKED
        summary = 'Backlog pressure is critical; require manual backlog review and preserve conservative runtime guardrails.'

    reason_codes = list(snapshot.reason_codes)
    reason_codes.append(f'pressure_state:{snapshot.pressure_state}')

    return GovernanceBacklogPressureDecision.objects.create(
        linked_pressure_snapshot=snapshot,
        decision_type=decision_type,
        decision_status=decision_status,
        decision_summary=summary,
        reason_codes=reason_codes,
        metadata={
            'snapshot_id': snapshot.id,
            'pressure_state': snapshot.pressure_state,
            'non_authoritative_signal': True,
        },
    )

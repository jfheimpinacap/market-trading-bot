from __future__ import annotations

from apps.runtime_governor.models import (
    RuntimeFeedbackDecision,
    RuntimeFeedbackDecisionStatus,
    RuntimeFeedbackDecisionType,
    RuntimeDiagnosticReview,
    RuntimePerformanceSnapshot,
)


def build_runtime_feedback_decision(*, snapshot: RuntimePerformanceSnapshot, diagnostic: RuntimeDiagnosticReview) -> RuntimeFeedbackDecision:
    reason_codes = sorted(set((snapshot.reason_codes or []) + (diagnostic.reason_codes or [])))
    governance_backlog_pressure_state = str((snapshot.metadata or {}).get('governance_backlog_pressure_state') or 'NORMAL').upper()

    decision_type = RuntimeFeedbackDecisionType.KEEP_CURRENT_GLOBAL_MODE
    auto_applicable = True
    summary = 'Keep current global mode; runtime remains within conservative limits.'

    if diagnostic.diagnostic_type == 'LOSS_RECOVERY_PRESSURE':
        decision_type = RuntimeFeedbackDecisionType.ENTER_RECOVERY_MODE
        summary = 'Enter recovery mode due to repeated recent losses.'
    elif diagnostic.diagnostic_type == 'OVERTRADING_PRESSURE':
        decision_type = RuntimeFeedbackDecisionType.SHIFT_TO_MORE_CONSERVATIVE_MODE
        summary = 'Shift to more conservative mode to reduce overtrading pressure.'
    elif diagnostic.diagnostic_type == 'BLOCKED_RUNTIME_SATURATION':
        decision_type = RuntimeFeedbackDecisionType.REDUCE_ADMISSION_AND_CADENCE
        summary = 'Reduce admission and cadence to relieve blocked/parked saturation.'
    elif diagnostic.diagnostic_type == 'QUIET_RUNTIME':
        decision_type = RuntimeFeedbackDecisionType.SHIFT_TO_MONITOR_ONLY
        summary = 'Shift temporarily to monitor-only while opportunity flow stays quiet.'
    elif diagnostic.diagnostic_type == 'LOW_QUALITY_OPPORTUNITY_FLOW':
        decision_type = RuntimeFeedbackDecisionType.SHIFT_TO_MORE_CONSERVATIVE_MODE
        summary = 'Shift conservatively while opportunity quality is weak.'

    if snapshot.current_global_mode == 'RECOVERY_MODE' and diagnostic.diagnostic_type == 'HEALTHY_RUNTIME':
        decision_type = RuntimeFeedbackDecisionType.RELAX_TO_CAUTION
        summary = 'Relax from recovery mode to caution after stabilized runtime signals.'
    if snapshot.current_global_mode == 'THROTTLED' and diagnostic.diagnostic_type == 'HEALTHY_RUNTIME':
        decision_type = RuntimeFeedbackDecisionType.RELAX_TO_CAUTION
        summary = 'Relax from throttled mode to caution after stabilized runtime signals.'

    if governance_backlog_pressure_state == 'CAUTION':
        reason_codes.append('backlog_caution_bias_conservative')
        if decision_type == RuntimeFeedbackDecisionType.KEEP_CURRENT_GLOBAL_MODE:
            decision_type = RuntimeFeedbackDecisionType.SHIFT_TO_MORE_CONSERVATIVE_MODE
            summary = 'Backlog pressure is CAUTION; apply a mild conservative runtime bias.'
        elif decision_type == RuntimeFeedbackDecisionType.RELAX_TO_CAUTION:
            summary = 'Backlog pressure is CAUTION; relaxation is allowed only to cautious posture.'
    elif governance_backlog_pressure_state == 'HIGH':
        reason_codes.extend(['backlog_high_relaxation_guard', 'backlog_high_manual_review_bias'])
        if decision_type == RuntimeFeedbackDecisionType.RELAX_TO_CAUTION:
            decision_type = RuntimeFeedbackDecisionType.REDUCE_ADMISSION_AND_CADENCE
            summary = 'Backlog pressure is HIGH; defer relaxation and reduce admission/cadence.'
        elif decision_type in {
            RuntimeFeedbackDecisionType.KEEP_CURRENT_GLOBAL_MODE,
            RuntimeFeedbackDecisionType.SHIFT_TO_MORE_CONSERVATIVE_MODE,
        }:
            decision_type = RuntimeFeedbackDecisionType.REDUCE_ADMISSION_AND_CADENCE
            summary = 'Backlog pressure is HIGH; favor reduced admission/cadence under conservative runtime tuning.'
    elif governance_backlog_pressure_state == 'CRITICAL':
        reason_codes.extend(['backlog_critical_relaxation_block', 'backlog_critical_manual_review_bias'])
        if decision_type == RuntimeFeedbackDecisionType.RELAX_TO_CAUTION:
            decision_type = RuntimeFeedbackDecisionType.REQUIRE_MANUAL_RUNTIME_REVIEW
            auto_applicable = False
            summary = 'Backlog pressure is CRITICAL; aggressive relaxation is blocked pending manual runtime review.'
        elif diagnostic.diagnostic_severity in {'INFO', 'CAUTION'}:
            decision_type = RuntimeFeedbackDecisionType.SHIFT_TO_MONITOR_ONLY
            summary = 'Backlog pressure is CRITICAL with non-severe runtime signals; bias to monitor-only posture.'
        elif decision_type != RuntimeFeedbackDecisionType.REQUIRE_MANUAL_RUNTIME_REVIEW:
            decision_type = RuntimeFeedbackDecisionType.REQUIRE_MANUAL_RUNTIME_REVIEW
            auto_applicable = False
            summary = 'Backlog pressure is CRITICAL; require manual runtime review before further mode changes.'

    if diagnostic.diagnostic_severity == 'CRITICAL' or (
        snapshot.recent_loss_count >= 3 and snapshot.recent_blocked_tick_count >= 2
    ):
        decision_type = RuntimeFeedbackDecisionType.REQUIRE_MANUAL_RUNTIME_REVIEW
        auto_applicable = False
        summary = 'Signals are critical or contradictory; require manual runtime review.'

    return RuntimeFeedbackDecision.objects.create(
        linked_performance_snapshot=snapshot,
        linked_diagnostic_review=diagnostic,
        decision_type=decision_type,
        decision_status=RuntimeFeedbackDecisionStatus.PROPOSED,
        auto_applicable=auto_applicable,
        decision_summary=summary,
        reason_codes=reason_codes,
        metadata={
            'current_global_mode': snapshot.current_global_mode,
            'diagnostic_type': diagnostic.diagnostic_type,
            'diagnostic_severity': diagnostic.diagnostic_severity,
            'governance_backlog_pressure_state': governance_backlog_pressure_state,
        },
    )

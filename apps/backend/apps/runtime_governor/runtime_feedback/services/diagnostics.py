from __future__ import annotations

from apps.runtime_governor.models import (
    RuntimeDiagnosticReview,
    RuntimeFeedbackDiagnosticSeverity,
    RuntimeFeedbackDiagnosticType,
    RuntimePerformanceSnapshot,
)


def build_runtime_diagnostic_review(*, snapshot: RuntimePerformanceSnapshot) -> RuntimeDiagnosticReview:
    reason_codes = list(snapshot.reason_codes or [])

    diagnostic_type = RuntimeFeedbackDiagnosticType.HEALTHY_RUNTIME
    severity = RuntimeFeedbackDiagnosticSeverity.INFO
    summary = 'Runtime remains healthy in the recent paper window.'

    if snapshot.recent_loss_count >= 3:
        diagnostic_type = RuntimeFeedbackDiagnosticType.LOSS_RECOVERY_PRESSURE
        severity = RuntimeFeedbackDiagnosticSeverity.HIGH
        summary = 'Recent closed loss exits are elevated and require recovery-oriented posture.'
        reason_codes.append('losses_above_threshold')
    elif snapshot.recent_dispatch_count >= 8 and snapshot.recent_exposure_throttle_count >= 1:
        diagnostic_type = RuntimeFeedbackDiagnosticType.OVERTRADING_PRESSURE
        severity = RuntimeFeedbackDiagnosticSeverity.HIGH
        summary = 'Dispatch velocity plus throttle events indicates potential overtrading pressure.'
        reason_codes.append('overtrading_pressure')
    elif snapshot.runtime_pressure_state == 'CRITICAL':
        diagnostic_type = RuntimeFeedbackDiagnosticType.BLOCKED_RUNTIME_SATURATION
        severity = RuntimeFeedbackDiagnosticSeverity.CRITICAL
        summary = 'Runtime pressure is critical due to blocked/parked/throttled saturation.'
        reason_codes.append('critical_runtime_pressure')
    elif snapshot.signal_quality_state == 'QUIET' and snapshot.recent_dispatch_count == 0:
        diagnostic_type = RuntimeFeedbackDiagnosticType.QUIET_RUNTIME
        severity = RuntimeFeedbackDiagnosticSeverity.CAUTION
        summary = 'Runtime is quiet with repeated no-action windows and low flow.'
        reason_codes.append('quiet_runtime_window')
    elif snapshot.signal_quality_state == 'WEAK':
        diagnostic_type = RuntimeFeedbackDiagnosticType.LOW_QUALITY_OPPORTUNITY_FLOW
        severity = RuntimeFeedbackDiagnosticSeverity.CAUTION
        summary = 'Recent opportunity quality is weak relative to outcomes and losses.'
        reason_codes.append('weak_opportunity_flow')
    elif snapshot.recent_blocked_tick_count >= 3 or snapshot.recent_parked_session_count >= 3:
        diagnostic_type = RuntimeFeedbackDiagnosticType.BLOCKED_RUNTIME_SATURATION
        severity = RuntimeFeedbackDiagnosticSeverity.HIGH
        summary = 'Runtime is saturated by blocked ticks or parked sessions.'
        reason_codes.append('blocked_runtime_saturation')

    return RuntimeDiagnosticReview.objects.create(
        linked_performance_snapshot=snapshot,
        diagnostic_type=diagnostic_type,
        diagnostic_severity=severity,
        diagnostic_summary=summary,
        reason_codes=sorted(set(reason_codes)),
        metadata={'signal_quality_state': snapshot.signal_quality_state, 'runtime_pressure_state': snapshot.runtime_pressure_state},
    )

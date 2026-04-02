from __future__ import annotations

from apps.mission_control.models import (
    AutonomousCapacityStatus,
    AutonomousGlobalCapacitySnapshot,
    AutonomousResumeDecision,
    AutonomousResumeDecisionType,
    AutonomousRuntimeSession,
    AutonomousRuntimeSessionStatus,
    AutonomousSessionAdmissionReview,
    AutonomousSessionAdmissionRun,
    AutonomousSessionAdmissionStatus,
    AutonomousSessionHealthSnapshot,
    AutonomousSessionHealthStatus,
    AutonomousSessionOperabilityState,
    AutonomousSessionPriorityState,
    AutonomousSessionRecoverySnapshot,
    AutonomousSessionContextReview,
)


def _priority(session: AutonomousRuntimeSession, context: AutonomousSessionContextReview | None) -> str:
    no_action = session.metadata.get('no_signal_streak', 0)
    if no_action >= 8:
        return AutonomousSessionPriorityState.NO_VALUE
    if no_action >= 5:
        return AutonomousSessionPriorityState.LOW_VALUE
    if session.dispatch_count >= 5:
        return AutonomousSessionPriorityState.HIGH_VALUE
    if context and context.signal_pressure_state == 'HIGH':
        return AutonomousSessionPriorityState.HIGH_VALUE
    return AutonomousSessionPriorityState.MEDIUM_VALUE


def evaluate_session_for_admission(*, session: AutonomousRuntimeSession, capacity_snapshot: AutonomousGlobalCapacitySnapshot, admission_run: AutonomousSessionAdmissionRun | None = None, running_rank: int = 0) -> AutonomousSessionAdmissionReview:
    latest_health = AutonomousSessionHealthSnapshot.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
    latest_recovery = AutonomousSessionRecoverySnapshot.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
    latest_context = AutonomousSessionContextReview.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
    latest_resume = AutonomousResumeDecision.objects.filter(linked_session=session).order_by('-created_at', '-id').first()

    priority = _priority(session, latest_context)
    reason_codes: list[str] = []

    if latest_health and latest_health.session_health_status in {AutonomousSessionHealthStatus.BLOCKED, AutonomousSessionHealthStatus.DEGRADED}:
        operability = AutonomousSessionOperabilityState.BLOCKED
        reason_codes.append('health_blocked_or_degraded')
    elif latest_recovery and latest_recovery.recovery_status in {'RECOVERED', 'PARTIALLY_RECOVERED'}:
        operability = AutonomousSessionOperabilityState.RECOVERABLE
    elif session.session_status == AutonomousRuntimeSessionStatus.RUNNING:
        operability = AutonomousSessionOperabilityState.READY
    else:
        operability = AutonomousSessionOperabilityState.CAUTION

    no_signal = session.metadata.get('no_signal_streak', 0)
    if priority == AutonomousSessionPriorityState.NO_VALUE or no_signal >= 10:
        operability = AutonomousSessionOperabilityState.RETIRE_CANDIDATE
        reason_codes.append('repeated_low_signal')

    if capacity_snapshot.capacity_status == AutonomousCapacityStatus.BLOCKED:
        status = AutonomousSessionAdmissionStatus.PAUSE
        reason_codes.append('global_capacity_blocked')
    elif operability == AutonomousSessionOperabilityState.RETIRE_CANDIDATE:
        status = AutonomousSessionAdmissionStatus.RETIRE
    elif operability == AutonomousSessionOperabilityState.BLOCKED:
        status = AutonomousSessionAdmissionStatus.MANUAL_REVIEW
    elif session.session_status == AutonomousRuntimeSessionStatus.PAUSED and latest_resume and latest_resume.decision_type == AutonomousResumeDecisionType.READY_TO_RESUME and capacity_snapshot.capacity_status == AutonomousCapacityStatus.AVAILABLE:
        status = AutonomousSessionAdmissionStatus.RESUME_ALLOWED
    elif session.session_status == AutonomousRuntimeSessionStatus.RUNNING:
        if running_rank <= capacity_snapshot.max_active_sessions:
            status = AutonomousSessionAdmissionStatus.ADMIT
        elif priority in {AutonomousSessionPriorityState.LOW_VALUE, AutonomousSessionPriorityState.NO_VALUE}:
            status = AutonomousSessionAdmissionStatus.PARK
        else:
            status = AutonomousSessionAdmissionStatus.DEFER
    elif capacity_snapshot.capacity_status == AutonomousCapacityStatus.AVAILABLE and operability in {AutonomousSessionOperabilityState.READY, AutonomousSessionOperabilityState.RECOVERABLE}:
        status = AutonomousSessionAdmissionStatus.ADMIT
    elif capacity_snapshot.capacity_status in {AutonomousCapacityStatus.LIMITED, AutonomousCapacityStatus.THROTTLED}:
        status = AutonomousSessionAdmissionStatus.DEFER if priority in {AutonomousSessionPriorityState.HIGH_VALUE, AutonomousSessionPriorityState.MEDIUM_VALUE} else AutonomousSessionAdmissionStatus.PARK
    else:
        status = AutonomousSessionAdmissionStatus.MANUAL_REVIEW

    summary = f'priority={priority} operability={operability} admission={status} capacity={capacity_snapshot.capacity_status}'
    return AutonomousSessionAdmissionReview.objects.create(
        linked_admission_run=admission_run,
        linked_session=session,
        linked_capacity_snapshot=capacity_snapshot,
        linked_latest_health_snapshot=latest_health,
        linked_latest_recovery_snapshot=latest_recovery,
        linked_latest_context_review=latest_context,
        linked_current_profile=session.linked_schedule_profile,
        session_priority_state=priority,
        session_operability_state=operability,
        admission_status=status,
        review_summary=summary,
        reason_codes=reason_codes,
        metadata={'running_rank': running_rank, 'latest_resume_decision': latest_resume.decision_type if latest_resume else None},
    )

from __future__ import annotations

from dataclasses import dataclass

from apps.runtime_governor.services import get_runtime_state
from apps.safety_guard.services import get_safety_status
from apps.mission_control.models import (
    AutonomousProfilePortfolioPressureState,
    AutonomousRuntimeSession,
    AutonomousSessionContextReview,
    AutonomousSessionHealthSnapshot,
    AutonomousSessionInterventionDecision,
    AutonomousSessionInterventionRecord,
    AutonomousSessionRecoveryRun,
    AutonomousSessionRecoverySnapshot,
    AutonomousSessionRecoveryStatus,
    AutonomousSessionTimingSnapshot,
)


@dataclass
class RecoverySnapshotResult:
    snapshot: AutonomousSessionRecoverySnapshot


def build_recovery_snapshot(*, session: AutonomousRuntimeSession, recovery_run: AutonomousSessionRecoveryRun | None = None) -> RecoverySnapshotResult:
    latest_health_snapshot = AutonomousSessionHealthSnapshot.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
    latest_intervention_decision = AutonomousSessionInterventionDecision.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
    latest_intervention_record = AutonomousSessionInterventionRecord.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
    latest_timing_snapshot = AutonomousSessionTimingSnapshot.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
    latest_context_review = AutonomousSessionContextReview.objects.filter(linked_session=session).order_by('-created_at', '-id').first()

    safety = get_safety_status()
    runtime_state = get_runtime_state()

    safety_block_cleared = not bool(safety.get('kill_switch_enabled') or safety.get('hard_stop_active'))
    runtime_block_cleared = runtime_state.current_mode != 'HALTED'

    incident_pressure_state = latest_health_snapshot.incident_pressure_state if latest_health_snapshot else 'NONE'
    incident_pressure_cleared = incident_pressure_state != 'HIGH'

    portfolio_pressure_state = (
        latest_context_review.portfolio_pressure_state
        if latest_context_review
        else AutonomousProfilePortfolioPressureState.NORMAL
    )

    cooldown_active = bool(latest_health_snapshot.has_active_cooldown) if latest_health_snapshot else False
    recent_failed_ticks = latest_health_snapshot.consecutive_failed_ticks if latest_health_snapshot else 0
    recent_blocked_ticks = latest_health_snapshot.consecutive_blocked_ticks if latest_health_snapshot else 0
    recent_successful_ticks = latest_health_snapshot.recent_dispatch_count if latest_health_snapshot else 0

    reason_codes: list[str] = []
    if not safety_block_cleared:
        reason_codes.append('safety_block_active')
    if not runtime_block_cleared:
        reason_codes.append('runtime_block_active')
    if not incident_pressure_cleared:
        reason_codes.append('incident_pressure_high')
    if portfolio_pressure_state in {
        AutonomousProfilePortfolioPressureState.THROTTLED,
        AutonomousProfilePortfolioPressureState.BLOCK_NEW_ENTRIES,
    }:
        reason_codes.append('portfolio_pressure_elevated')
    if cooldown_active:
        reason_codes.append('cooldown_active')
    if recent_failed_ticks >= 3:
        reason_codes.append('recent_failure_streak')
    if recent_blocked_ticks >= 3:
        reason_codes.append('recent_blocked_streak')

    if not safety_block_cleared or not runtime_block_cleared:
        recovery_status = AutonomousSessionRecoveryStatus.STILL_BLOCKED
    elif not incident_pressure_cleared:
        recovery_status = AutonomousSessionRecoveryStatus.STILL_BLOCKED
    elif recent_failed_ticks >= 5 or recent_blocked_ticks >= 5:
        recovery_status = AutonomousSessionRecoveryStatus.UNRECOVERABLE
    elif recent_failed_ticks >= 2 or recent_blocked_ticks >= 2 or cooldown_active:
        recovery_status = AutonomousSessionRecoveryStatus.STABILIZING
    elif portfolio_pressure_state in {
        AutonomousProfilePortfolioPressureState.CAUTION,
        AutonomousProfilePortfolioPressureState.THROTTLED,
        AutonomousProfilePortfolioPressureState.BLOCK_NEW_ENTRIES,
    }:
        recovery_status = AutonomousSessionRecoveryStatus.PARTIALLY_RECOVERED
    else:
        recovery_status = AutonomousSessionRecoveryStatus.RECOVERED

    summary = (
        f'recovery={recovery_status} safety_cleared={safety_block_cleared} runtime_cleared={runtime_block_cleared} '
        f'incident_cleared={incident_pressure_cleared} failed={recent_failed_ticks} blocked={recent_blocked_ticks} '
        f'successful={recent_successful_ticks}'
    )

    snapshot = AutonomousSessionRecoverySnapshot.objects.create(
        linked_recovery_run=recovery_run,
        linked_session=session,
        linked_latest_health_snapshot=latest_health_snapshot,
        linked_latest_intervention_decision=latest_intervention_decision,
        linked_latest_intervention_record=latest_intervention_record,
        linked_latest_timing_snapshot=latest_timing_snapshot,
        recovery_status=recovery_status,
        safety_block_cleared=safety_block_cleared,
        runtime_block_cleared=runtime_block_cleared,
        incident_pressure_cleared=incident_pressure_cleared,
        portfolio_pressure_state=portfolio_pressure_state,
        cooldown_active=cooldown_active,
        recent_failed_ticks=recent_failed_ticks,
        recent_blocked_ticks=recent_blocked_ticks,
        recent_successful_ticks=recent_successful_ticks,
        recovery_summary=summary,
        reason_codes=reason_codes,
        metadata={
            'session_status': session.session_status,
            'runtime_mode': runtime_state.current_mode,
            'incident_pressure_state': incident_pressure_state,
        },
    )
    return RecoverySnapshotResult(snapshot=snapshot)

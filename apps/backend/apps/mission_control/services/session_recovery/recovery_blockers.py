from __future__ import annotations

from apps.mission_control.models import (
    AutonomousProfilePortfolioPressureState,
    AutonomousRecoveryBlocker,
    AutonomousRecoveryBlockerSeverity,
    AutonomousRecoveryBlockerType,
    AutonomousSessionRecoverySnapshot,
)


def detect_recovery_blockers(*, snapshot: AutonomousSessionRecoverySnapshot) -> list[AutonomousRecoveryBlocker]:
    blockers: list[AutonomousRecoveryBlocker] = []

    def _add(blocker_type: str, severity: str, summary: str, reason_codes: list[str]) -> None:
        blockers.append(
            AutonomousRecoveryBlocker.objects.create(
                linked_session=snapshot.linked_session,
                linked_recovery_snapshot=snapshot,
                blocker_type=blocker_type,
                blocker_severity=severity,
                blocker_summary=summary,
                reason_codes=reason_codes,
                metadata={},
            )
        )

    if not snapshot.safety_block_cleared:
        _add(
            AutonomousRecoveryBlockerType.SAFETY_BLOCK_ACTIVE,
            AutonomousRecoveryBlockerSeverity.CRITICAL,
            f'Safety block remains active for session={snapshot.linked_session_id}.',
            ['safety_block_active'],
        )

    if not snapshot.runtime_block_cleared:
        _add(
            AutonomousRecoveryBlockerType.RUNTIME_BLOCK_ACTIVE,
            AutonomousRecoveryBlockerSeverity.CRITICAL,
            f'Runtime hard block remains active for session={snapshot.linked_session_id}.',
            ['runtime_block_active'],
        )

    if not snapshot.incident_pressure_cleared:
        _add(
            AutonomousRecoveryBlockerType.INCIDENT_PRESSURE_ACTIVE,
            AutonomousRecoveryBlockerSeverity.HIGH,
            f'Incident pressure is still elevated for session={snapshot.linked_session_id}.',
            ['incident_pressure_high'],
        )

    if snapshot.portfolio_pressure_state in {
        AutonomousProfilePortfolioPressureState.THROTTLED,
        AutonomousProfilePortfolioPressureState.BLOCK_NEW_ENTRIES,
    }:
        _add(
            AutonomousRecoveryBlockerType.PORTFOLIO_PRESSURE_ACTIVE,
            AutonomousRecoveryBlockerSeverity.HIGH,
            f'Portfolio pressure is {snapshot.portfolio_pressure_state} for session={snapshot.linked_session_id}.',
            ['portfolio_pressure_elevated'],
        )

    if snapshot.cooldown_active:
        _add(
            AutonomousRecoveryBlockerType.COOLDOWN_ACTIVE,
            AutonomousRecoveryBlockerSeverity.CAUTION,
            f'Cooldown is active for session={snapshot.linked_session_id}.',
            ['cooldown_active'],
        )

    if snapshot.recent_failed_ticks >= 3:
        _add(
            AutonomousRecoveryBlockerType.RECENT_FAILURE_STREAK,
            AutonomousRecoveryBlockerSeverity.HIGH,
            f'Recent failed streak={snapshot.recent_failed_ticks} for session={snapshot.linked_session_id}.',
            ['recent_failure_streak'],
        )

    if snapshot.recent_blocked_ticks >= 3:
        _add(
            AutonomousRecoveryBlockerType.RECENT_BLOCKED_STREAK,
            AutonomousRecoveryBlockerSeverity.HIGH,
            f'Recent blocked streak={snapshot.recent_blocked_ticks} for session={snapshot.linked_session_id}.',
            ['recent_blocked_streak'],
        )

    if snapshot.recovery_status in {'UNRECOVERABLE', 'STABILIZING'} and (snapshot.recent_failed_ticks >= 4 or snapshot.recent_blocked_ticks >= 4):
        _add(
            AutonomousRecoveryBlockerType.MANUAL_REVIEW_REQUIRED,
            AutonomousRecoveryBlockerSeverity.CRITICAL if snapshot.recovery_status == 'UNRECOVERABLE' else AutonomousRecoveryBlockerSeverity.HIGH,
            f'Manual recovery review required for session={snapshot.linked_session_id}.',
            ['manual_review_required'],
        )

    return blockers

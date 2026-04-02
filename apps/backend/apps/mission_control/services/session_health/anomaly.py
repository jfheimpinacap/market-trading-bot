from __future__ import annotations

from apps.mission_control.models import (
    AutonomousIncidentPressureState,
    AutonomousSessionAnomaly,
    AutonomousSessionAnomalySeverity,
    AutonomousSessionAnomalyType,
    AutonomousSessionHealthSnapshot,
)


def detect_anomalies(*, snapshot: AutonomousSessionHealthSnapshot) -> list[AutonomousSessionAnomaly]:
    anomalies: list[AutonomousSessionAnomaly] = []

    if snapshot.consecutive_failed_ticks >= 2:
        severity = AutonomousSessionAnomalySeverity.HIGH if snapshot.consecutive_failed_ticks >= 4 else AutonomousSessionAnomalySeverity.CAUTION
        anomalies.append(
            AutonomousSessionAnomaly.objects.create(
                linked_session=snapshot.linked_session,
                linked_health_snapshot=snapshot,
                anomaly_type=AutonomousSessionAnomalyType.REPEATED_FAILED_TICKS,
                anomaly_severity=severity,
                anomaly_summary=f'{snapshot.consecutive_failed_ticks} consecutive failed ticks detected.',
                reason_codes=['failed_tick_streak'],
                metadata={'consecutive_failed_ticks': snapshot.consecutive_failed_ticks},
            )
        )

    if snapshot.consecutive_blocked_ticks >= 2:
        severity = AutonomousSessionAnomalySeverity.CRITICAL if snapshot.consecutive_blocked_ticks >= 4 else AutonomousSessionAnomalySeverity.HIGH
        anomalies.append(
            AutonomousSessionAnomaly.objects.create(
                linked_session=snapshot.linked_session,
                linked_health_snapshot=snapshot,
                anomaly_type=AutonomousSessionAnomalyType.REPEATED_BLOCKED_TICKS,
                anomaly_severity=severity,
                anomaly_summary=f'{snapshot.consecutive_blocked_ticks} consecutive blocked ticks detected.',
                reason_codes=['blocked_tick_streak'],
                metadata={'consecutive_blocked_ticks': snapshot.consecutive_blocked_ticks},
            )
        )

    if snapshot.runner_session_mismatch:
        anomalies.append(
            AutonomousSessionAnomaly.objects.create(
                linked_session=snapshot.linked_session,
                linked_health_snapshot=snapshot,
                anomaly_type=AutonomousSessionAnomalyType.RUNNER_SESSION_MISMATCH,
                anomaly_severity=AutonomousSessionAnomalySeverity.HIGH,
                anomaly_summary='Runner/session mismatch detected between RUNNING runner and session state.',
                reason_codes=['runner_session_mismatch'],
                metadata={'runner_state': snapshot.linked_runner_state.runner_status if snapshot.linked_runner_state else None},
            )
        )

    if snapshot.consecutive_no_progress_ticks >= 5:
        anomalies.append(
            AutonomousSessionAnomaly.objects.create(
                linked_session=snapshot.linked_session,
                linked_health_snapshot=snapshot,
                anomaly_type=AutonomousSessionAnomalyType.STALE_SESSION_NO_PROGRESS,
                anomaly_severity=AutonomousSessionAnomalySeverity.CAUTION,
                anomaly_summary='Session appears stale with prolonged no-progress ticks.',
                reason_codes=['stale_no_progress'],
                metadata={'consecutive_no_progress_ticks': snapshot.consecutive_no_progress_ticks},
            )
        )

    if snapshot.linked_session.session_status == 'PAUSED' and snapshot.consecutive_no_progress_ticks >= 3:
        anomalies.append(
            AutonomousSessionAnomaly.objects.create(
                linked_session=snapshot.linked_session,
                linked_health_snapshot=snapshot,
                anomaly_type=AutonomousSessionAnomalyType.PERSISTENT_PAUSE,
                anomaly_severity=AutonomousSessionAnomalySeverity.CAUTION,
                anomaly_summary='Session remains paused with unresolved progression blockers.',
                reason_codes=['persistent_pause'],
                metadata={'pause_reason_codes': snapshot.linked_session.pause_reason_codes},
            )
        )

    if snapshot.metadata.get('hard_block'):
        anomalies.append(
            AutonomousSessionAnomaly.objects.create(
                linked_session=snapshot.linked_session,
                linked_health_snapshot=snapshot,
                anomaly_type=AutonomousSessionAnomalyType.SAFETY_OR_RUNTIME_PRESSURE,
                anomaly_severity=AutonomousSessionAnomalySeverity.CRITICAL,
                anomaly_summary='Safety/runtime hard block requires immediate conservative intervention.',
                reason_codes=['hard_block'],
                metadata={'runtime_mode': snapshot.metadata.get('runtime_mode')},
            )
        )

    if snapshot.incident_pressure_state == AutonomousIncidentPressureState.HIGH:
        anomalies.append(
            AutonomousSessionAnomaly.objects.create(
                linked_session=snapshot.linked_session,
                linked_health_snapshot=snapshot,
                anomaly_type=AutonomousSessionAnomalyType.INCIDENT_ESCALATION_PRESSURE,
                anomaly_severity=AutonomousSessionAnomalySeverity.HIGH,
                anomaly_summary='Incident pressure is high; escalation path is preferred.',
                reason_codes=['incident_pressure_high'],
                metadata={'related_open_incidents': snapshot.metadata.get('related_open_incidents', 0)},
            )
        )

    if snapshot.recent_loss_count >= 2:
        anomalies.append(
            AutonomousSessionAnomaly.objects.create(
                linked_session=snapshot.linked_session,
                linked_health_snapshot=snapshot,
                anomaly_type=AutonomousSessionAnomalyType.POST_LOSS_STABILIZATION_REQUIRED,
                anomaly_severity=AutonomousSessionAnomalySeverity.CAUTION,
                anomaly_summary='Repeated recent losses indicate a stabilization window is needed.',
                reason_codes=['post_loss_stabilization'],
                metadata={'recent_loss_count': snapshot.recent_loss_count},
            )
        )

    return anomalies

from __future__ import annotations

from apps.mission_control.models import (
    AutonomousStopConditionEvaluation,
    AutonomousStopEvaluationStatus,
    AutonomousStopEvaluationType,
    AutonomousTimingDecisionType,
    AutonomousSessionTimingSnapshot,
)


def evaluate_stop_conditions(*, snapshot: AutonomousSessionTimingSnapshot, decision_type: str) -> list[AutonomousStopConditionEvaluation]:
    evaluations: list[AutonomousStopConditionEvaluation] = []

    if snapshot.consecutive_blocked_ticks > 0:
        status = AutonomousStopEvaluationStatus.ACTIONABLE if decision_type == AutonomousTimingDecisionType.STOP_SESSION else AutonomousStopEvaluationStatus.CAUTION
        evaluations.append(
            AutonomousStopConditionEvaluation.objects.create(
                linked_session=snapshot.linked_session,
                evaluation_type=AutonomousStopEvaluationType.PERSISTENT_BLOCKS,
                evaluation_status=status,
                evaluation_summary='Persistent blocked ticks detected in recent cadence window.',
                reason_codes=['blocked_ticks', *snapshot.reason_codes],
                metadata={'consecutive_blocked_ticks': snapshot.consecutive_blocked_ticks},
            )
        )

    if snapshot.consecutive_no_action_ticks > 0:
        status = AutonomousStopEvaluationStatus.ACTIONABLE if decision_type == AutonomousTimingDecisionType.PAUSE_SESSION else AutonomousStopEvaluationStatus.CAUTION
        evaluations.append(
            AutonomousStopConditionEvaluation.objects.create(
                linked_session=snapshot.linked_session,
                evaluation_type=AutonomousStopEvaluationType.QUIET_MARKET,
                evaluation_status=status,
                evaluation_summary='Repeated no-action/watch-only ticks suggest quiet market regime.',
                reason_codes=['quiet_market', *snapshot.reason_codes],
                metadata={'consecutive_no_action_ticks': snapshot.consecutive_no_action_ticks},
            )
        )

    if snapshot.recent_loss_count > 0:
        evaluations.append(
            AutonomousStopConditionEvaluation.objects.create(
                linked_session=snapshot.linked_session,
                evaluation_type=AutonomousStopEvaluationType.POST_LOSS_COOLDOWN,
                evaluation_status=AutonomousStopEvaluationStatus.CAUTION,
                evaluation_summary='Recent loss detected; cooldown/monitor-only cadence enforced.',
                reason_codes=['recent_loss', *snapshot.reason_codes],
                metadata={'recent_loss_count': snapshot.recent_loss_count},
            )
        )

    return evaluations

from __future__ import annotations

from apps.mission_control.models import (
    AutonomousCadenceDecision,
    AutonomousCadenceMode,
    AutonomousRuntimeTick,
    AutonomousSessionRecommendation,
    AutonomousSessionRecommendationType,
)


def emit_session_recommendation(*, cadence_decision: AutonomousCadenceDecision, tick: AutonomousRuntimeTick | None = None) -> AutonomousSessionRecommendation:
    rec_type = AutonomousSessionRecommendationType.CONTINUE_RUNNING
    blockers: list[str] = []

    if cadence_decision.cadence_mode == AutonomousCadenceMode.STOP_SESSION:
        rec_type = AutonomousSessionRecommendationType.STOP_FOR_RUNTIME_HARD_BLOCK
        blockers = list(cadence_decision.cadence_reason_codes or [])
    elif cadence_decision.cadence_mode == AutonomousCadenceMode.PAUSE_SESSION:
        rec_type = AutonomousSessionRecommendationType.PAUSE_FOR_SAFETY_BLOCK
        blockers = list(cadence_decision.cadence_reason_codes or [])
    elif cadence_decision.cadence_mode == AutonomousCadenceMode.MONITOR_ONLY_NEXT:
        rec_type = AutonomousSessionRecommendationType.RUN_REDUCED_NEXT_TICK
    elif cadence_decision.cadence_mode in {AutonomousCadenceMode.WAIT_SHORT, AutonomousCadenceMode.WAIT_LONG}:
        rec_type = AutonomousSessionRecommendationType.WAIT_FOR_SIGNAL_REFRESH

    return AutonomousSessionRecommendation.objects.create(
        recommendation_type=rec_type,
        target_session=cadence_decision.linked_session,
        target_tick=tick,
        target_cadence_decision=cadence_decision,
        rationale=f'{cadence_decision.decision_summary} Recommendation={rec_type}.',
        reason_codes=list(cadence_decision.cadence_reason_codes or []),
        confidence=0.9 if blockers else 0.75,
        blockers=blockers,
    )

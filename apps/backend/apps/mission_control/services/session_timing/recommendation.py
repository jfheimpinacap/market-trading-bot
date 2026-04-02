from __future__ import annotations

from apps.mission_control.models import (
    AutonomousTimingDecision,
    AutonomousTimingDecisionType,
    AutonomousTimingRecommendation,
    AutonomousTimingRecommendationType,
    AutonomousSessionTimingSnapshot,
)


def emit_timing_recommendation(*, snapshot: AutonomousSessionTimingSnapshot, decision: AutonomousTimingDecision) -> AutonomousTimingRecommendation:
    recommendation_type = AutonomousTimingRecommendationType.REQUIRE_MANUAL_TIMING_REVIEW
    rationale = 'Manual timing review recommended.'
    confidence = 0.5

    if decision.decision_type == AutonomousTimingDecisionType.RUN_NOW:
        recommendation_type = AutonomousTimingRecommendationType.RUN_NEXT_TICK_IMMEDIATELY
        rationale = 'No active cooldown/pressure detected, session can run immediately.'
        confidence = 0.8
    elif decision.decision_type == AutonomousTimingDecisionType.WAIT_SHORT:
        recommendation_type = AutonomousTimingRecommendationType.WAIT_FOR_SHORT_INTERVAL
        rationale = 'Short wait recommended to reduce cadence noise while preserving responsiveness.'
        confidence = 0.75
    elif decision.decision_type == AutonomousTimingDecisionType.WAIT_LONG:
        recommendation_type = AutonomousTimingRecommendationType.WAIT_FOR_LONG_INTERVAL
        rationale = 'Long wait recommended due to quiet market or cooldown extension signals.'
        confidence = 0.76
    elif decision.decision_type == AutonomousTimingDecisionType.MONITOR_ONLY_NEXT:
        recommendation_type = AutonomousTimingRecommendationType.ENTER_MONITOR_ONLY_WINDOW
        rationale = 'Monitor-only window recommended after elevated caution/loss pressure.'
        confidence = 0.77
    elif decision.decision_type == AutonomousTimingDecisionType.PAUSE_SESSION:
        recommendation_type = AutonomousTimingRecommendationType.PAUSE_SESSION_FOR_QUIET_MARKET
        rationale = 'Auto-pause recommended due to persistent no-action quiet market regime.'
        confidence = 0.82
    elif decision.decision_type == AutonomousTimingDecisionType.STOP_SESSION:
        recommendation_type = AutonomousTimingRecommendationType.STOP_SESSION_FOR_PERSISTENT_BLOCKS
        rationale = 'Persistent blocked ticks reached stop threshold; manual intervention required.'
        confidence = 0.88

    blockers = [] if recommendation_type in {
        AutonomousTimingRecommendationType.RUN_NEXT_TICK_IMMEDIATELY,
        AutonomousTimingRecommendationType.WAIT_FOR_SHORT_INTERVAL,
        AutonomousTimingRecommendationType.WAIT_FOR_LONG_INTERVAL,
        AutonomousTimingRecommendationType.ENTER_MONITOR_ONLY_WINDOW,
    } else ['manual_governance_review']

    return AutonomousTimingRecommendation.objects.create(
        recommendation_type=recommendation_type,
        target_session=snapshot.linked_session,
        target_timing_snapshot=snapshot,
        target_timing_decision=decision,
        rationale=rationale,
        reason_codes=snapshot.reason_codes,
        confidence=confidence,
        blockers=blockers,
    )

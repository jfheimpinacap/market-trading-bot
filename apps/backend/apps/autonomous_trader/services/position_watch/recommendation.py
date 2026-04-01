from __future__ import annotations

from apps.autonomous_trader.models import (
    AutonomousPositionActionDecisionType,
    AutonomousPositionWatchRecommendation,
    AutonomousPositionWatchRecommendationType,
)


def emit_recommendation(*, candidate, decision) -> AutonomousPositionWatchRecommendation:
    rec_type = AutonomousPositionWatchRecommendationType.KEEP_HOLDING_POSITION
    blockers: list[str] = []
    if decision.decision_type == AutonomousPositionActionDecisionType.REDUCE_POSITION:
        if 'PORTFOLIO_PRESSURE' in (decision.reason_codes or []):
            rec_type = AutonomousPositionWatchRecommendationType.REDUCE_FOR_PORTFOLIO_PRESSURE
        else:
            rec_type = AutonomousPositionWatchRecommendationType.REDUCE_FOR_SENTIMENT_WEAKENING
    elif decision.decision_type == AutonomousPositionActionDecisionType.CLOSE_POSITION:
        if 'RISK_BLOCKED' in (decision.reason_codes or []):
            rec_type = AutonomousPositionWatchRecommendationType.CLOSE_FOR_RISK_DETERIORATION
        else:
            rec_type = AutonomousPositionWatchRecommendationType.CLOSE_FOR_NARRATIVE_REVERSAL
    elif decision.decision_type == AutonomousPositionActionDecisionType.REVIEW_REQUIRED:
        rec_type = AutonomousPositionWatchRecommendationType.REQUIRE_MANUAL_REVIEW_FOR_SIGNAL_CONFLICT
        blockers = ['SIGNAL_CONFLICT']

    return AutonomousPositionWatchRecommendation.objects.create(
        recommendation_type=rec_type,
        target_position=candidate.linked_position,
        target_watch_candidate=candidate,
        target_action_decision=decision,
        rationale='Conservative autonomous post-entry recommendation generated from watch assessment and decision.',
        reason_codes=decision.reason_codes,
        confidence=decision.decision_confidence,
        blockers=blockers,
        metadata={'paper_only': True},
    )

from __future__ import annotations

from decimal import Decimal

from apps.autonomous_trader.models import (
    AutonomousPortfolioPressureState,
    AutonomousPositionActionDecision,
    AutonomousPositionActionDecisionStatus,
    AutonomousPositionActionDecisionType,
    AutonomousPositionWatchCandidateStatus,
    AutonomousRiskState,
    AutonomousSentimentState,
)


def decide_action(*, candidate, assessment: dict) -> AutonomousPositionActionDecision:
    reasons = list(assessment.get('reason_codes') or [])
    decision_type = AutonomousPositionActionDecisionType.HOLD_POSITION
    confidence = Decimal('0.7000')
    reduction_fraction = None
    status = AutonomousPositionActionDecisionStatus.PROPOSED

    conflicting = candidate.sentiment_state == AutonomousSentimentState.IMPROVING and candidate.risk_state in {AutonomousRiskState.ELEVATED, AutonomousRiskState.BLOCKED}
    if conflicting:
        decision_type = AutonomousPositionActionDecisionType.REVIEW_REQUIRED
        candidate.candidate_status = AutonomousPositionWatchCandidateStatus.REVIEW_REQUIRED
        confidence = Decimal('0.6200')
        reasons.append('SIGNAL_CONFLICT')
    elif candidate.risk_state == AutonomousRiskState.BLOCKED or candidate.sentiment_state == AutonomousSentimentState.REVERSING:
        decision_type = AutonomousPositionActionDecisionType.CLOSE_POSITION
        candidate.candidate_status = AutonomousPositionWatchCandidateStatus.CLOSE_ELIGIBLE
        confidence = Decimal('0.9100')
    elif 'EDGE_DECAY_CRITICAL' in reasons:
        decision_type = AutonomousPositionActionDecisionType.CLOSE_POSITION
        candidate.candidate_status = AutonomousPositionWatchCandidateStatus.CLOSE_ELIGIBLE
        confidence = Decimal('0.8600')
    elif (
        candidate.sentiment_state == AutonomousSentimentState.WEAKENING
        or 'EDGE_DECAY' in reasons
        or candidate.portfolio_pressure_state in {AutonomousPortfolioPressureState.CAUTION, AutonomousPortfolioPressureState.THROTTLED, AutonomousPortfolioPressureState.BLOCK_NEW_ENTRIES}
    ):
        decision_type = AutonomousPositionActionDecisionType.REDUCE_POSITION
        candidate.candidate_status = AutonomousPositionWatchCandidateStatus.REDUCE_ELIGIBLE
        reduction_fraction = Decimal('0.2500')
        confidence = Decimal('0.7800')
        if candidate.portfolio_pressure_state in {AutonomousPortfolioPressureState.THROTTLED, AutonomousPortfolioPressureState.BLOCK_NEW_ENTRIES}:
            reduction_fraction = Decimal('0.5000')
    else:
        candidate.candidate_status = AutonomousPositionWatchCandidateStatus.NO_ACTION

    candidate.save(update_fields=['candidate_status', 'updated_at'])
    return AutonomousPositionActionDecision.objects.create(
        linked_watch_candidate=candidate,
        decision_type=decision_type,
        decision_status=status,
        decision_confidence=confidence,
        reduction_fraction=reduction_fraction,
        rationale='Autonomous post-entry watch decision using explicit conservative rules.',
        reason_codes=reasons,
        metadata={'paper_only': True, 'assessment': assessment},
    )

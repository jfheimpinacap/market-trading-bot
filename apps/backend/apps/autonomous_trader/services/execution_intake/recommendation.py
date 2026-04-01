from __future__ import annotations

from apps.autonomous_trader.models import (
    AutonomousExecutionDecision,
    AutonomousExecutionDecisionType,
    AutonomousExecutionRecommendation,
    AutonomousExecutionRecommendationType,
)


def create_recommendation(*, decision: AutonomousExecutionDecision, dispatch_record=None) -> AutonomousExecutionRecommendation:
    mapping = {
        AutonomousExecutionDecisionType.EXECUTE_NOW: AutonomousExecutionRecommendationType.AUTO_EXECUTE_NOW,
        AutonomousExecutionDecisionType.EXECUTE_REDUCED: AutonomousExecutionRecommendationType.AUTO_EXECUTE_REDUCED,
        AutonomousExecutionDecisionType.KEEP_ON_WATCH: AutonomousExecutionRecommendationType.KEEP_ON_AUTONOMOUS_WATCH,
        AutonomousExecutionDecisionType.DEFER: AutonomousExecutionRecommendationType.DEFER_FOR_WEAKER_READINESS,
        AutonomousExecutionDecisionType.BLOCK: AutonomousExecutionRecommendationType.BLOCK_FOR_POLICY_OR_RUNTIME,
        AutonomousExecutionDecisionType.REQUIRE_MANUAL_REVIEW: AutonomousExecutionRecommendationType.REQUIRE_MANUAL_REVIEW_FOR_EXECUTION_CONFLICT,
    }
    recommendation_type = mapping[decision.decision_type]
    blockers = []
    if decision.decision_type in {AutonomousExecutionDecisionType.BLOCK, AutonomousExecutionDecisionType.REQUIRE_MANUAL_REVIEW}:
        blockers = decision.reason_codes

    return AutonomousExecutionRecommendation.objects.create(
        linked_intake_run=decision.linked_intake_candidate.intake_run,
        recommendation_type=recommendation_type,
        target_market=decision.linked_intake_candidate.linked_market,
        target_intake_candidate=decision.linked_intake_candidate,
        target_execution_decision=decision,
        target_dispatch=dispatch_record,
        rationale=decision.rationale,
        reason_codes=decision.reason_codes,
        confidence=decision.decision_confidence,
        blockers=blockers,
    )

from __future__ import annotations

from decimal import Decimal

from apps.autonomous_trader.models import (
    AutonomousFeedbackInfluenceRecord,
    AutonomousFeedbackRecommendation,
    AutonomousFeedbackRecommendationType,
)


def create_feedback_recommendation(*, influence: AutonomousFeedbackInfluenceRecord) -> AutonomousFeedbackRecommendation:
    recommendation_type = AutonomousFeedbackRecommendationType.KEEP_ON_WATCH_WITH_MEMORY_CONTEXT
    reason_codes = influence.influence_reason_codes or []
    blockers: list[str] = []
    rationale = influence.influence_summary
    confidence = Decimal('0.6200')

    if 'NO_RELEVANT_LEARNING_FOUND' in reason_codes:
        recommendation_type = AutonomousFeedbackRecommendationType.NO_RELEVANT_LEARNING_FOUND
        confidence = Decimal('0.7000')
    elif influence.influence_type == 'BLOCK_REPEAT_PATTERN':
        recommendation_type = AutonomousFeedbackRecommendationType.BLOCK_REPEAT_LOSS_PATTERN
        confidence = Decimal('0.8600')
    elif influence.influence_type == 'CONFIDENCE_REDUCTION':
        recommendation_type = AutonomousFeedbackRecommendationType.REDUCE_CONFIDENCE_FOR_REPEAT_PATTERN
        confidence = Decimal('0.8000')
    elif influence.influence_type == 'CAUTION_BOOST':
        recommendation_type = AutonomousFeedbackRecommendationType.APPLY_CAUTION_BOOST
        confidence = Decimal('0.7600')

    if influence.influence_status == 'BLOCKED':
        recommendation_type = AutonomousFeedbackRecommendationType.REQUIRE_MANUAL_REVIEW_FOR_MEMORY_CONFLICT
        blockers = ['MEMORY_RETRIEVAL_UNAVAILABLE']
        confidence = Decimal('0.5100')

    return AutonomousFeedbackRecommendation.objects.create(
        recommendation_type=recommendation_type,
        target_candidate=influence.linked_candidate,
        target_context=influence.linked_candidate_context,
        target_influence_record=influence,
        rationale=rationale,
        reason_codes=reason_codes,
        confidence=confidence,
        blockers=blockers,
        metadata={
            'paper_only': True,
            'bounded_influence': True,
        },
    )

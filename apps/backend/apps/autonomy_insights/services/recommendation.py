from __future__ import annotations

from apps.autonomy_insights.models import InsightRecommendationType, InsightType


def build_insight_recommendations(*, insight, pending_review_count: int) -> list[dict]:
    recommendation_type = InsightRecommendationType.REQUIRE_OPERATOR_REVIEW
    confidence = 0.65

    if insight.insight_type == InsightType.SUCCESS_PATTERN:
        recommendation_type = InsightRecommendationType.REGISTER_MEMORY_PRECEDENT
        confidence = 0.84
    elif insight.insight_type == InsightType.FAILURE_PATTERN:
        recommendation_type = InsightRecommendationType.PREPARE_ROADMAP_GOVERNANCE_NOTE
        confidence = 0.79
    elif insight.insight_type == InsightType.BLOCKER_PATTERN:
        recommendation_type = InsightRecommendationType.PREPARE_PROGRAM_POLICY_NOTE
        confidence = 0.76
    elif insight.insight_type == InsightType.GOVERNANCE_PATTERN:
        recommendation_type = InsightRecommendationType.PREPARE_SCENARIO_CAUTION
        confidence = 0.73

    recommendations = [
        {
            'target_campaign_id': insight.campaign_id,
            'campaign_insight_id': insight.id,
            'recommendation_type': recommendation_type,
            'insight_type': insight.insight_type,
            'rationale': insight.recommended_followup or insight.summary,
            'reason_codes': insight.reason_codes,
            'confidence': confidence,
            'blockers': [],
            'metadata': {'insight_scope': insight.scope},
        }
    ]

    if pending_review_count > 3:
        recommendations.append(
            {
                'target_campaign_id': None,
                'campaign_insight_id': None,
                'recommendation_type': InsightRecommendationType.REORDER_INSIGHT_PRIORITY,
                'insight_type': InsightType.GOVERNANCE_PATTERN,
                'rationale': 'Multiple unresolved insights compete for operator attention; reorder by confidence and domain risk.',
                'reason_codes': ['too_many_pending_insights'],
                'confidence': 0.62,
                'blockers': [],
                'metadata': {'pending_review_count': pending_review_count},
            }
        )

    return recommendations

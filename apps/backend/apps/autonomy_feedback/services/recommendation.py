from __future__ import annotations

from apps.autonomy_feedback.models import FeedbackRecommendationType, ResolutionStatus
from apps.autonomy_followup.models import FollowupType


def build_resolution_recommendations(*, resolution, pending_candidate_count: int) -> list[dict]:
    recommendation_type = FeedbackRecommendationType.KEEP_PENDING
    confidence = 0.6
    rationale = resolution.rationale

    if resolution.resolution_status == ResolutionStatus.COMPLETED:
        recommendation_type = FeedbackRecommendationType.MARK_FOLLOWUP_COMPLETED
        confidence = 0.82
        rationale = 'Downstream evidence indicates this follow-up can be manually closed.'
    elif resolution.resolution_status in {ResolutionStatus.BLOCKED, ResolutionStatus.REJECTED}:
        recommendation_type = FeedbackRecommendationType.REQUIRE_MANUAL_REVIEW
        confidence = 0.76
        rationale = 'Follow-up is blocked/rejected and requires operator intervention.'
    elif resolution.followup.followup_type == FollowupType.MEMORY_INDEX:
        recommendation_type = FeedbackRecommendationType.REVIEW_MEMORY_RESOLUTION
        confidence = 0.66
    elif resolution.followup.followup_type == FollowupType.POSTMORTEM_REQUEST:
        recommendation_type = FeedbackRecommendationType.REVIEW_POSTMORTEM_RESOLUTION
        confidence = 0.66
    elif resolution.followup.followup_type == FollowupType.ROADMAP_FEEDBACK:
        recommendation_type = FeedbackRecommendationType.REVIEW_ROADMAP_FEEDBACK_STATUS
        confidence = 0.64

    recommendations = [
        {
            'target_campaign_id': resolution.campaign_id,
            'followup_id': resolution.followup_id,
            'followup_type': resolution.followup.followup_type,
            'recommendation_type': recommendation_type,
            'rationale': rationale,
            'reason_codes': resolution.reason_codes,
            'confidence': confidence,
            'blockers': resolution.blockers,
            'metadata': {'resolution_status': resolution.resolution_status},
        }
    ]

    if pending_candidate_count > 1:
        recommendations.append(
            {
                'target_campaign_id': None,
                'followup_id': None,
                'followup_type': '',
                'recommendation_type': FeedbackRecommendationType.REORDER_FEEDBACK_PRIORITY,
                'rationale': 'Multiple emitted follow-ups remain unresolved; prioritize by blocker severity and age.',
                'reason_codes': ['multiple_pending_followups'],
                'confidence': 0.61,
                'blockers': [],
                'metadata': {'pending_candidate_count': pending_candidate_count},
            }
        )

    return recommendations

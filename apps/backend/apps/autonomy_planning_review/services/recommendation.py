from __future__ import annotations

from apps.autonomy_planning_review.models import (
    PlanningProposalResolution,
    PlanningProposalResolutionStatus,
    PlanningReviewRecommendationType,
)


def build_planning_recommendations(*, resolution: PlanningProposalResolution, pending_count: int) -> list[dict]:
    recommendations: list[dict] = []

    if resolution.resolution_status == PlanningProposalResolutionStatus.PENDING:
        recommendations.append(
            {
                'recommendation_type': PlanningReviewRecommendationType.ACKNOWLEDGE_PROPOSAL,
                'rationale': 'Proposal was emitted but not yet acknowledged. Confirm manual review before accept/defer/reject.',
                'reason_codes': ['pending_acknowledgment'],
                'confidence': '0.8200',
                'blockers': resolution.blockers,
                'metadata': {'resolution_id': resolution.id},
            }
        )
        recommendations.append(
            {
                'recommendation_type': PlanningReviewRecommendationType.KEEP_PENDING,
                'rationale': 'Keep pending when downstream roadmap/scenario/program/manager evidence is still insufficient.',
                'reason_codes': ['insufficient_downstream_signal'],
                'confidence': '0.6100',
                'blockers': resolution.blockers,
                'metadata': {'resolution_id': resolution.id},
            }
        )
    elif resolution.resolution_status == PlanningProposalResolutionStatus.ACKNOWLEDGED:
        recommendations.append(
            {
                'recommendation_type': PlanningReviewRecommendationType.MARK_ACCEPTED,
                'rationale': 'Acknowledged proposal can be marked accepted once governance confirms future planning adoption intent.',
                'reason_codes': ['awaiting_adoption_decision'],
                'confidence': '0.7300',
                'blockers': resolution.blockers,
                'metadata': {'resolution_id': resolution.id},
            }
        )
    elif resolution.resolution_status == PlanningProposalResolutionStatus.BLOCKED:
        recommendations.append(
            {
                'recommendation_type': PlanningReviewRecommendationType.REQUIRE_MANUAL_REVIEW,
                'rationale': 'Blocked proposal requires manual review to resolve blockers or formally defer/reject.',
                'reason_codes': ['blocked_proposal'],
                'confidence': '0.9000',
                'blockers': resolution.blockers,
                'metadata': {'resolution_id': resolution.id},
            }
        )

    if pending_count > 1:
        recommendations.append(
            {
                'recommendation_type': PlanningReviewRecommendationType.REORDER_PLANNING_REVIEW_PRIORITY,
                'rationale': f'{pending_count} proposals remain pending; reorder review queue by target scope and priority.',
                'reason_codes': ['multiple_pending_resolutions'],
                'confidence': '0.7900',
                'blockers': [],
                'metadata': {'pending_count': pending_count},
            }
        )

    return recommendations

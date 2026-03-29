from __future__ import annotations

from apps.autonomy_backlog.models import BacklogRecommendationType, GovernanceBacklogStatus
from apps.autonomy_backlog.services.candidates import BacklogCandidate


def build_backlog_recommendations(*, candidate: BacklogCandidate, has_duplicate: bool, existing_status: str | None, queue_size: int) -> list[dict]:
    recommendations: list[dict] = []

    if candidate.blockers:
        recommendations.append(
            {
                'recommendation_type': BacklogRecommendationType.REQUIRE_MANUAL_BACKLOG_REVIEW,
                'rationale': 'Candidate has blockers and requires manual backlog review before registration.',
                'reason_codes': ['candidate_blocked'],
                'confidence': '0.9200',
                'blockers': candidate.blockers,
                'metadata': {'candidate_artifact': candidate.advisory_artifact},
            }
        )
        return recommendations

    if has_duplicate:
        recommendations.append(
            {
                'recommendation_type': BacklogRecommendationType.SKIP_DUPLICATE_BACKLOG,
                'rationale': 'Equivalent backlog item already exists for this advisory artifact.',
                'reason_codes': ['duplicate_backlog_item'],
                'confidence': '0.9500',
                'blockers': [],
                'metadata': {'candidate_artifact': candidate.advisory_artifact},
            }
        )
        if existing_status == GovernanceBacklogStatus.READY:
            recommendations.append(
                {
                    'recommendation_type': BacklogRecommendationType.PRIORITIZE_BACKLOG_ITEM,
                    'rationale': 'Existing READY item can be moved to PRIORITIZED state after operator review.',
                    'reason_codes': ['existing_item_ready'],
                    'confidence': '0.7300',
                    'blockers': [],
                    'metadata': {'candidate_artifact': candidate.advisory_artifact},
                }
            )
    elif candidate.ready_for_backlog:
        recommendations.append(
            {
                'recommendation_type': BacklogRecommendationType.CREATE_BACKLOG_ITEM,
                'rationale': 'Candidate is adopted/acknowledged and ready for governance backlog registration.',
                'reason_codes': ['ready_for_backlog_registration'],
                'confidence': '0.8400',
                'blockers': [],
                'metadata': {'candidate_artifact': candidate.advisory_artifact},
            }
        )

    if queue_size > 1:
        recommendations.append(
            {
                'recommendation_type': BacklogRecommendationType.REORDER_BACKLOG_PRIORITY,
                'rationale': f'{queue_size} ready candidates compete for governance attention; reorder by explicit priority levels.',
                'reason_codes': ['queue_competition'],
                'confidence': '0.7900',
                'blockers': [],
                'metadata': {'ready_queue_size': queue_size},
            }
        )

    return recommendations

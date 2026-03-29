from __future__ import annotations

from apps.autonomy_advisory_resolution.models import AdvisoryResolution, AdvisoryResolutionRecommendationType, AdvisoryResolutionStatus


def build_resolution_recommendations(*, resolution: AdvisoryResolution, pending_count: int) -> list[dict]:
    recommendations: list[dict] = []

    if resolution.resolution_status == AdvisoryResolutionStatus.PENDING:
        recommendations.append(
            {
                'recommendation_type': AdvisoryResolutionRecommendationType.ACKNOWLEDGE_ADVISORY,
                'rationale': 'Advisory has been emitted but not yet acknowledged. Confirm manual review before adoption/defer/reject.',
                'reason_codes': ['pending_acknowledgment'],
                'confidence': '0.8200',
                'blockers': resolution.blockers,
                'metadata': {'resolution_id': resolution.id},
            }
        )
        recommendations.append(
            {
                'recommendation_type': AdvisoryResolutionRecommendationType.KEEP_PENDING,
                'rationale': 'Keep as pending when there is still insufficient downstream evidence for adoption.',
                'reason_codes': ['insufficient_downstream_signal'],
                'confidence': '0.6100',
                'blockers': resolution.blockers,
                'metadata': {'resolution_id': resolution.id},
            }
        )
    elif resolution.resolution_status == AdvisoryResolutionStatus.ACKNOWLEDGED:
        recommendations.append(
            {
                'recommendation_type': AdvisoryResolutionRecommendationType.MARK_ADOPTED,
                'rationale': 'Acknowledged advisory can now be marked adopted once used as future planning input.',
                'reason_codes': ['awaiting_adoption_decision'],
                'confidence': '0.7300',
                'blockers': resolution.blockers,
                'metadata': {'resolution_id': resolution.id},
            }
        )
    elif resolution.resolution_status == AdvisoryResolutionStatus.BLOCKED:
        recommendations.append(
            {
                'recommendation_type': AdvisoryResolutionRecommendationType.REQUIRE_MANUAL_REVIEW,
                'rationale': 'Blocked advisories need manual review to resolve blockers or document rejection/defer.',
                'reason_codes': ['blocked_artifact'],
                'confidence': '0.9000',
                'blockers': resolution.blockers,
                'metadata': {'resolution_id': resolution.id},
            }
        )

    if pending_count > 1:
        recommendations.append(
            {
                'recommendation_type': AdvisoryResolutionRecommendationType.REORDER_ADVISORY_RESOLUTION_PRIORITY,
                'rationale': f'{pending_count} advisories remain pending; reorder queue by campaign criticality and recency.',
                'reason_codes': ['multiple_pending_resolutions'],
                'confidence': '0.7900',
                'blockers': [],
                'metadata': {'pending_count': pending_count},
            }
        )

    return recommendations

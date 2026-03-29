from apps.autonomy_package.models import PackageRecommendationType

RECOMMENDATION_BY_SCOPE = {
    'roadmap': PackageRecommendationType.REGISTER_ROADMAP_PACKAGE,
    'scenario': PackageRecommendationType.REGISTER_SCENARIO_PACKAGE,
    'program': PackageRecommendationType.REGISTER_PROGRAM_PACKAGE,
    'manager': PackageRecommendationType.REGISTER_MANAGER_PACKAGE,
    'operator_review': PackageRecommendationType.REQUIRE_MANUAL_PACKAGE_REVIEW,
}


def build_package_recommendations(*, candidate: dict, ready_count: int) -> list[dict]:
    recommendations: list[dict] = []

    if candidate['existing_package']:
        recommendations.append(
            {
                'recommendation_type': PackageRecommendationType.SKIP_DUPLICATE_PACKAGE,
                'rationale': 'A registered package already exists for this grouping key and target scope.',
                'reason_codes': ['package_duplicate'],
                'confidence': '0.9800',
                'blockers': [],
                'metadata': {'existing_package_id': candidate['existing_package']},
            }
        )
    elif candidate['blockers']:
        recommendations.append(
            {
                'recommendation_type': PackageRecommendationType.REQUIRE_MANUAL_PACKAGE_REVIEW,
                'rationale': 'Candidate cannot be packaged automatically due to blockers or missing fields.',
                'reason_codes': ['candidate_blocked'],
                'confidence': '0.8800',
                'blockers': candidate['blockers'],
                'metadata': {},
            }
        )
    else:
        recommendations.append(
            {
                'recommendation_type': RECOMMENDATION_BY_SCOPE.get(candidate['target_scope'], PackageRecommendationType.REQUIRE_MANUAL_PACKAGE_REVIEW),
                'rationale': 'Registered governance decision is ready to be grouped into an auditable next-cycle package seed.',
                'reason_codes': ['decision_ready_for_packaging'],
                'confidence': '0.8100',
                'blockers': [],
                'metadata': {'target_scope': candidate['target_scope']},
            }
        )

    if ready_count > 1:
        recommendations.append(
            {
                'recommendation_type': PackageRecommendationType.REORDER_PACKAGE_PRIORITY,
                'rationale': f"{ready_count} packaging candidates are ready; review bundle priority ordering before registration.",
                'reason_codes': ['multi_ready_queue'],
                'confidence': '0.7600',
                'blockers': [],
                'metadata': {'ready_count': ready_count},
            }
        )

    return recommendations

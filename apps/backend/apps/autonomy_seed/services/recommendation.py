from apps.autonomy_seed.models import GovernanceSeedType, SeedRecommendationType

RECOMMENDATION_BY_SCOPE = {
    'roadmap': (SeedRecommendationType.REGISTER_ROADMAP_SEED, GovernanceSeedType.ROADMAP_SEED),
    'scenario': (SeedRecommendationType.REGISTER_SCENARIO_SEED, GovernanceSeedType.SCENARIO_SEED),
    'program': (SeedRecommendationType.REGISTER_PROGRAM_SEED, GovernanceSeedType.PROGRAM_SEED),
    'manager': (SeedRecommendationType.REGISTER_MANAGER_SEED, GovernanceSeedType.MANAGER_SEED),
    'operator_review': (SeedRecommendationType.REQUIRE_MANUAL_SEED_REVIEW, GovernanceSeedType.OPERATOR_REVIEW_SEED),
}


def build_seed_recommendations(*, candidate: dict, ready_count: int) -> list[dict]:
    recommendations: list[dict] = []

    recommendation_type, seed_type = RECOMMENDATION_BY_SCOPE.get(
        candidate['target_scope'], (SeedRecommendationType.REQUIRE_MANUAL_SEED_REVIEW, GovernanceSeedType.OPERATOR_REVIEW_SEED)
    )

    if candidate['existing_seed']:
        recommendations.append(
            {
                'recommendation_type': SeedRecommendationType.SKIP_DUPLICATE_SEED,
                'seed_type': seed_type,
                'rationale': 'A governance seed for this package and target scope is already registered.',
                'reason_codes': ['seed_duplicate'],
                'confidence': '0.9800',
                'blockers': [],
                'metadata': {'existing_seed_id': candidate['existing_seed']},
            }
        )
    elif candidate['blockers']:
        recommendations.append(
            {
                'recommendation_type': SeedRecommendationType.REQUIRE_MANUAL_SEED_REVIEW,
                'seed_type': seed_type,
                'rationale': 'Adopted package requires manual seed review due to blockers or missing data.',
                'reason_codes': ['candidate_blocked'],
                'confidence': '0.8600',
                'blockers': candidate['blockers'],
                'metadata': {},
            }
        )
    else:
        recommendations.append(
            {
                'recommendation_type': recommendation_type,
                'seed_type': seed_type,
                'rationale': 'Adopted package is ready to be registered as a next-cycle planning seed.',
                'reason_codes': ['adopted_package_ready_for_seed'],
                'confidence': '0.8200',
                'blockers': [],
                'metadata': {'target_scope': candidate['target_scope']},
            }
        )

    if ready_count > 1:
        recommendations.append(
            {
                'recommendation_type': SeedRecommendationType.REORDER_SEED_PRIORITY,
                'seed_type': seed_type,
                'rationale': f'{ready_count} seed candidates are ready; reorder queue priority before registration.',
                'reason_codes': ['multi_ready_seed_queue'],
                'confidence': '0.7600',
                'blockers': [],
                'metadata': {'ready_count': ready_count},
            }
        )

    return recommendations

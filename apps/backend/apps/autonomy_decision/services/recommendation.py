from apps.autonomy_decision.models import DecisionRecommendationType


RECOMMENDATION_BY_SCOPE = {
    'roadmap': DecisionRecommendationType.REGISTER_ROADMAP_DECISION,
    'scenario': DecisionRecommendationType.REGISTER_SCENARIO_DECISION,
    'program': DecisionRecommendationType.REGISTER_PROGRAM_DECISION,
    'manager': DecisionRecommendationType.REGISTER_MANAGER_DECISION,
    'operator_review': DecisionRecommendationType.REQUIRE_MANUAL_DECISION_REVIEW,
}


def build_decision_recommendations(*, candidate: dict, ready_count: int) -> list[dict]:
    recommendations: list[dict] = []

    if candidate['existing_decision']:
        recommendations.append(
            {
                'recommendation_type': DecisionRecommendationType.SKIP_DUPLICATE_DECISION,
                'rationale': 'A registered governance decision already exists for this proposal and target scope.',
                'reason_codes': ['decision_duplicate'],
                'confidence': '0.9800',
                'blockers': [],
                'metadata': {'existing_decision_id': candidate['existing_decision']},
            }
        )
    elif candidate['blockers']:
        recommendations.append(
            {
                'recommendation_type': DecisionRecommendationType.REQUIRE_MANUAL_DECISION_REVIEW,
                'rationale': 'Candidate cannot be registered automatically due to blockers or missing fields.',
                'reason_codes': ['candidate_blocked'],
                'confidence': '0.8800',
                'blockers': candidate['blockers'],
                'metadata': {},
            }
        )
    else:
        recommendations.append(
            {
                'recommendation_type': RECOMMENDATION_BY_SCOPE.get(candidate['target_scope'], DecisionRecommendationType.REQUIRE_MANUAL_DECISION_REVIEW),
                'rationale': 'Accepted proposal is ready to be formalized into a governance decision artifact for the next cycle.',
                'reason_codes': ['accepted_ready_for_registration'],
                'confidence': '0.8100',
                'blockers': [],
                'metadata': {'target_scope': candidate['target_scope']},
            }
        )

    if ready_count > 1:
        recommendations.append(
            {
                'recommendation_type': DecisionRecommendationType.REORDER_DECISION_PRIORITY,
                'rationale': f'{ready_count} accepted proposals are decision-ready; review priority ordering before registration.',
                'reason_codes': ['multi_ready_queue'],
                'confidence': '0.7600',
                'blockers': [],
                'metadata': {'ready_count': ready_count},
            }
        )

    return recommendations

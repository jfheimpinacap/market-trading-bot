from __future__ import annotations

from decimal import Decimal

from apps.experiment_lab.models import (
    ChampionChallengerComparisonStatus,
    ExperimentCandidate,
    ExperimentPromotionRecommendationType,
    TuningChampionChallengerComparison,
)


def build_recommendation(*, candidate: ExperimentCandidate, comparison: TuningChampionChallengerComparison, bundle_size: int) -> dict:
    reason_codes = list(comparison.reason_codes or [])
    blockers = list(candidate.blockers or [])

    if comparison.comparison_status == ChampionChallengerComparisonStatus.NEEDS_MORE_DATA:
        recommendation_type = ExperimentPromotionRecommendationType.REQUIRE_MORE_DATA
        rationale = 'Comparison has insufficient sample size; gather more paper/replay evidence.'
    elif comparison.comparison_status == ChampionChallengerComparisonStatus.IMPROVED:
        recommendation_type = ExperimentPromotionRecommendationType.PROMOTE_TO_MANUAL_REVIEW
        rationale = 'Challenger improved key metrics and is ready for manual governance review.'
    elif comparison.comparison_status == ChampionChallengerComparisonStatus.DEGRADED:
        recommendation_type = ExperimentPromotionRecommendationType.REJECT_CHALLENGER
        rationale = 'Challenger degraded key metrics and should not advance.'
    elif comparison.comparison_status == ChampionChallengerComparisonStatus.MIXED:
        recommendation_type = ExperimentPromotionRecommendationType.KEEP_BASELINE
        rationale = 'Signals are mixed; keep baseline until degradations are resolved.'
    else:
        recommendation_type = ExperimentPromotionRecommendationType.REQUIRE_MORE_DATA
        rationale = 'Result is inconclusive; keep challenger in observation mode.'

    if bundle_size > 1 and recommendation_type in {
        ExperimentPromotionRecommendationType.PROMOTE_TO_MANUAL_REVIEW,
        ExperimentPromotionRecommendationType.KEEP_BASELINE,
    }:
        recommendation_type = ExperimentPromotionRecommendationType.BUNDLE_WITH_OTHER_CHANGES
        reason_codes.append('shared_problem_cluster')
        rationale = 'Candidate is part of a multi-proposal cluster; review together as a bounded bundle.'

    confidence = Decimal(comparison.confidence_score)
    if recommendation_type == ExperimentPromotionRecommendationType.REQUIRE_MORE_DATA:
        confidence = min(confidence, Decimal('0.50'))

    return {
        'target_candidate': candidate,
        'target_comparison': comparison,
        'recommendation_type': recommendation_type,
        'rationale': rationale,
        'reason_codes': reason_codes,
        'confidence': confidence,
        'blockers': blockers,
        'metadata': {
            'manual_first': True,
            'auto_apply': False,
            'paper_only': True,
        },
    }

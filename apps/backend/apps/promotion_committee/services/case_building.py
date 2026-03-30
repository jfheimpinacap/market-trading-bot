from __future__ import annotations

from dataclasses import dataclass

from apps.experiment_lab.models import (
    ChampionChallengerComparisonStatus,
    ExperimentCandidate,
    ExperimentPromotionRecommendation,
    ExperimentPromotionRecommendationType,
    TuningChampionChallengerComparison,
)
from apps.promotion_committee.models import (
    PromotionCase,
    PromotionChangeType,
    PromotionPriorityLevel,
    PromotionReviewCycleRun,
    PromotionTargetComponent,
)


@dataclass
class PromotionCaseContext:
    case: PromotionCase
    comparison: TuningChampionChallengerComparison | None
    recommendation: ExperimentPromotionRecommendation | None


def _component_from_candidate_type(candidate_type: str) -> str:
    mapping = {
        'threshold_challenger': PromotionTargetComponent.PREDICTION,
        'calibration_variant': PromotionTargetComponent.CALIBRATION,
        'risk_gate_variant': PromotionTargetComponent.RISK,
        'sizing_variant': PromotionTargetComponent.RISK,
        'shortlist_variant': PromotionTargetComponent.RESEARCH,
        'opportunity_variant': PromotionTargetComponent.OPPORTUNITY_CYCLE,
        'learning_weight_variant': PromotionTargetComponent.LEARNING,
    }
    return mapping.get(candidate_type, PromotionTargetComponent.PREDICTION)


def _change_type_from_candidate_type(candidate_type: str) -> str:
    mapping = {
        'threshold_challenger': PromotionChangeType.THRESHOLD_UPDATE,
        'calibration_variant': PromotionChangeType.CALIBRATION_UPDATE,
        'risk_gate_variant': PromotionChangeType.RISK_GATE_UPDATE,
        'sizing_variant': PromotionChangeType.SIZE_CAP_UPDATE,
        'shortlist_variant': PromotionChangeType.SHORTLIST_UPDATE,
        'opportunity_variant': PromotionChangeType.REVIEW_RULE_UPDATE,
        'learning_weight_variant': PromotionChangeType.CAUTION_WEIGHT_UPDATE,
    }
    return mapping.get(candidate_type, PromotionChangeType.CONVICTION_UPDATE)


def _priority_from_rows(comparison: TuningChampionChallengerComparison | None, recommendation: ExperimentPromotionRecommendation | None) -> str:
    confidence = float(comparison.confidence_score) if comparison else 0.0
    if recommendation and recommendation.recommendation_type == ExperimentPromotionRecommendationType.REJECT_CHALLENGER:
        return PromotionPriorityLevel.LOW
    if confidence >= 0.85:
        return PromotionPriorityLevel.CRITICAL
    if confidence >= 0.70:
        return PromotionPriorityLevel.HIGH
    if confidence >= 0.45:
        return PromotionPriorityLevel.MEDIUM
    return PromotionPriorityLevel.LOW


def build_promotion_cases(*, review_run: PromotionReviewCycleRun, linked_experiment_run_id: int | None = None) -> list[PromotionCaseContext]:
    comparisons = TuningChampionChallengerComparison.objects.select_related(
        'linked_candidate', 'linked_candidate__linked_tuning_proposal', 'linked_candidate__linked_tuning_bundle', 'run'
    ).order_by('-created_at', '-id')
    if linked_experiment_run_id:
        comparisons = comparisons.filter(run_id=linked_experiment_run_id)

    recommendation_by_comparison = {
        row.target_comparison_id: row
        for row in ExperimentPromotionRecommendation.objects.select_related('target_candidate', 'target_comparison')
        .filter(target_comparison_id__in=comparisons.values_list('id', flat=True))
        .order_by('-created_at', '-id')
    }

    contexts: list[PromotionCaseContext] = []
    for comparison in comparisons[:200]:
        candidate: ExperimentCandidate = comparison.linked_candidate
        recommendation = recommendation_by_comparison.get(comparison.id)
        reason_codes = list(comparison.reason_codes or [])
        if recommendation:
            reason_codes.extend(code for code in recommendation.reason_codes if code not in reason_codes)

        blockers = list(candidate.blockers or [])
        if comparison.comparison_status in {
            ChampionChallengerComparisonStatus.INCONCLUSIVE,
            ChampionChallengerComparisonStatus.NEEDS_MORE_DATA,
        } and 'comparison_needs_more_data' not in blockers:
            blockers.append('comparison_needs_more_data')

        case = PromotionCase.objects.create(
            review_run=review_run,
            linked_experiment_candidate=candidate,
            linked_comparison=comparison,
            linked_tuning_proposal=candidate.linked_tuning_proposal,
            linked_bundle=candidate.linked_tuning_bundle,
            target_component=_component_from_candidate_type(candidate.candidate_type),
            target_scope=candidate.experiment_scope,
            change_type=_change_type_from_candidate_type(candidate.candidate_type),
            priority_level=_priority_from_rows(comparison, recommendation),
            current_value=str(comparison.compared_metrics.get('baseline_value', '')),
            proposed_value=str(comparison.compared_metrics.get('challenger_value', '')),
            rationale=recommendation.rationale if recommendation else comparison.rationale,
            blockers=blockers,
            reason_codes=reason_codes,
            metadata={
                'comparison_status': comparison.comparison_status,
                'candidate_readiness_status': candidate.readiness_status,
                'experiment_run_id': comparison.run_id,
                'promotion_recommendation_type': recommendation.recommendation_type if recommendation else None,
            },
        )
        contexts.append(PromotionCaseContext(case=case, comparison=comparison, recommendation=recommendation))

    return contexts

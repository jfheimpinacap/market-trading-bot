from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.experiment_lab.models import (
    ChampionChallengerComparisonStatus,
    ExperimentCandidate,
    ExperimentPromotionRecommendation,
    TuningChampionChallengerComparison,
    TuningExperimentRun,
)
from apps.experiment_lab.services.baseline_challenger import map_baseline_and_challenger
from apps.experiment_lab.services.candidate_building import build_candidate_specs
from apps.experiment_lab.services.recommendation import build_recommendation
from apps.experiment_lab.services.tuning_comparison import build_comparison_for_candidate
from apps.tuning_board.models import TuningProposal, TuningProposalBundle, TuningReviewRun


def _latest_tuning_review(explicit_id: int | None = None) -> TuningReviewRun | None:
    if explicit_id:
        return TuningReviewRun.objects.filter(pk=explicit_id).first()
    return TuningReviewRun.objects.order_by('-started_at', '-id').first()


def run_tuning_validation(*, linked_tuning_review_run_id: int | None = None, metadata: dict | None = None) -> TuningExperimentRun:
    metadata = metadata or {}
    linked_run = _latest_tuning_review(linked_tuning_review_run_id)
    proposal_queryset = TuningProposal.objects.select_related('run', 'source_metric').order_by('-created_at', '-id')
    if linked_run:
        proposal_queryset = proposal_queryset.filter(run=linked_run)

    proposals = list(proposal_queryset[:100])
    proposal_ids = [item.id for item in proposals]
    bundles = TuningProposalBundle.objects.filter(linked_proposals__id__in=proposal_ids).prefetch_related('linked_proposals').distinct()
    proposal_to_bundle = {}
    bundle_sizes: dict[int, int] = {}
    for bundle in bundles:
        linked = list(bundle.linked_proposals.values_list('id', flat=True))
        for proposal_id in linked:
            proposal_to_bundle[proposal_id] = bundle
            bundle_sizes[proposal_id] = len(linked)

    with transaction.atomic():
        run = TuningExperimentRun.objects.create(
            started_at=timezone.now(),
            linked_tuning_review_run=linked_run,
            metadata={**metadata, 'paper_only': True, 'auto_apply': False},
        )

        specs = build_candidate_specs(proposals=proposals, proposal_to_bundle=proposal_to_bundle)
        candidates = [ExperimentCandidate(run=run, **spec) for spec in specs]
        ExperimentCandidate.objects.bulk_create(candidates)
        candidates = list(run.candidates.select_related('linked_tuning_proposal').order_by('id'))

        comparisons: list[TuningChampionChallengerComparison] = []
        recommendations: list[ExperimentPromotionRecommendation] = []

        for candidate in candidates:
            mapping = map_baseline_and_challenger(candidate=candidate)
            comparison_payload = build_comparison_for_candidate(
                candidate=candidate,
                baseline_label=mapping['baseline_label'],
                challenger_label=mapping['challenger_label'],
            )
            comparison = TuningChampionChallengerComparison.objects.create(run=run, **comparison_payload)
            comparisons.append(comparison)

            recommendation_payload = build_recommendation(
                candidate=candidate,
                comparison=comparison,
                bundle_size=bundle_sizes.get(candidate.linked_tuning_proposal_id, 1),
            )
            recommendation = ExperimentPromotionRecommendation.objects.create(run=run, **recommendation_payload)
            recommendations.append(recommendation)

        improved = sum(1 for item in comparisons if item.comparison_status == ChampionChallengerComparisonStatus.IMPROVED)
        degraded = sum(1 for item in comparisons if item.comparison_status == ChampionChallengerComparisonStatus.DEGRADED)
        more_data = sum(1 for item in comparisons if item.comparison_status in {ChampionChallengerComparisonStatus.NEEDS_MORE_DATA, ChampionChallengerComparisonStatus.INCONCLUSIVE})

        run.candidate_count = len(candidates)
        run.comparison_count = len(comparisons)
        run.improved_count = improved
        run.degraded_count = degraded
        run.require_more_data_count = more_data
        run.recommendation_summary = {
            'PROMOTE_TO_MANUAL_REVIEW': sum(1 for item in recommendations if item.recommendation_type == 'PROMOTE_TO_MANUAL_REVIEW'),
            'KEEP_BASELINE': sum(1 for item in recommendations if item.recommendation_type == 'KEEP_BASELINE'),
            'REQUIRE_MORE_DATA': sum(1 for item in recommendations if item.recommendation_type == 'REQUIRE_MORE_DATA'),
            'REJECT_CHALLENGER': sum(1 for item in recommendations if item.recommendation_type == 'REJECT_CHALLENGER'),
            'BUNDLE_WITH_OTHER_CHANGES': sum(1 for item in recommendations if item.recommendation_type == 'BUNDLE_WITH_OTHER_CHANGES'),
        }
        run.completed_at = timezone.now()
        run.save()

    return run


def build_tuning_validation_summary() -> dict:
    latest = TuningExperimentRun.objects.order_by('-started_at', '-id').first()
    if latest is None:
        return {
            'latest_run': None,
            'candidates_reviewed': 0,
            'comparisons_run': 0,
            'improved': 0,
            'degraded': 0,
            'inconclusive': 0,
            'ready_for_manual_review': 0,
        }

    comparisons = latest.comparisons.all()
    recommendations = latest.promotion_recommendations.all()
    return {
        'latest_run': latest.id,
        'candidates_reviewed': latest.candidate_count,
        'comparisons_run': latest.comparison_count,
        'improved': latest.improved_count,
        'degraded': latest.degraded_count,
        'inconclusive': sum(1 for item in comparisons if item.comparison_status in {'INCONCLUSIVE', 'NEEDS_MORE_DATA'}),
        'ready_for_manual_review': sum(1 for item in recommendations if item.recommendation_type == 'PROMOTE_TO_MANUAL_REVIEW'),
        'recommendation_summary': latest.recommendation_summary,
        'manual_first': True,
        'paper_only': True,
        'auto_promotion': False,
    }

from __future__ import annotations

from collections import Counter, defaultdict

from django.db import transaction
from django.utils import timezone

from apps.experiment_lab.models import TuningExperimentRun
from apps.promotion_committee.models import (
    PromotionCaseStatus,
    PromotionPriorityLevel,
    PromotionReviewCycleRun,
)
from apps.promotion_committee.services.case_building import build_promotion_cases
from apps.promotion_committee.services.evidence_pack import build_evidence_pack
from apps.promotion_committee.services.readiness import classify_case_readiness
from apps.promotion_committee.services.recommendation import (
    create_case_recommendation,
    create_grouping_recommendation,
    create_reorder_recommendation,
)


@transaction.atomic
def run_governed_promotion_review(*, actor: str = 'promotion_ui', linked_experiment_run_id: int | None = None, metadata: dict | None = None):
    run = PromotionReviewCycleRun.objects.create(
        started_at=timezone.now(),
        linked_experiment_run=TuningExperimentRun.objects.filter(id=linked_experiment_run_id).first() if linked_experiment_run_id else None,
        metadata={'actor': actor, **(metadata or {})},
    )

    case_contexts = build_promotion_cases(review_run=run, linked_experiment_run_id=linked_experiment_run_id)
    case_ids_by_signature: dict[tuple[str, str], list[int]] = defaultdict(list)

    for context in case_contexts:
        evidence = build_evidence_pack(promotion_case=context.case)
        case_status = classify_case_readiness(promotion_case=context.case, evidence_pack=evidence)
        if case_status == PromotionCaseStatus.READY_FOR_REVIEW and context.case.priority_level == PromotionPriorityLevel.CRITICAL:
            case_status = PromotionCaseStatus.APPROVED_FOR_MANUAL_ADOPTION
        context.case.case_status = case_status
        context.case.save(update_fields=['case_status', 'updated_at'])
        case_ids_by_signature[(context.case.target_component, context.case.target_scope)].append(context.case.id)
        create_case_recommendation(review_run=run, case=context.case, evidence_pack=evidence)

    for _, grouped_ids in case_ids_by_signature.items():
        create_grouping_recommendation(review_run=run, grouped_case_ids=grouped_ids)

    high_priority_ids = list(
        run.cases.filter(priority_level__in=[PromotionPriorityLevel.HIGH, PromotionPriorityLevel.CRITICAL]).values_list('id', flat=True)
    )
    create_reorder_recommendation(review_run=run, high_priority_case_ids=high_priority_ids)

    status_counter = Counter(run.cases.values_list('case_status', flat=True))
    recommendation_counter = Counter(run.decision_recommendations.values_list('recommendation_type', flat=True))

    run.candidate_count = run.cases.count()
    run.ready_for_review_count = status_counter.get(PromotionCaseStatus.READY_FOR_REVIEW, 0) + status_counter.get(PromotionCaseStatus.APPROVED_FOR_MANUAL_ADOPTION, 0)
    run.needs_more_data_count = status_counter.get(PromotionCaseStatus.NEEDS_MORE_DATA, 0)
    run.deferred_count = status_counter.get(PromotionCaseStatus.DEFERRED, 0)
    run.rejected_count = status_counter.get(PromotionCaseStatus.REJECTED, 0)
    run.high_priority_count = run.cases.filter(priority_level__in=[PromotionPriorityLevel.HIGH, PromotionPriorityLevel.CRITICAL]).count()
    run.recommendation_summary = dict(recommendation_counter)
    run.completed_at = timezone.now()
    run.save(
        update_fields=[
            'candidate_count',
            'ready_for_review_count',
            'needs_more_data_count',
            'deferred_count',
            'rejected_count',
            'high_priority_count',
            'recommendation_summary',
            'completed_at',
            'updated_at',
        ]
    )

    return run

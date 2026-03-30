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
from apps.promotion_committee.services.candidate_building import build_adoption_candidates
from apps.promotion_committee.services.action_planning import plan_manual_action
from apps.promotion_committee.services.recommendation import create_adoption_recommendation
from apps.promotion_committee.services.rollback import prepare_rollback_plan
from apps.promotion_committee.services.recommendation import (
    create_case_recommendation,
    create_grouping_recommendation,
    create_reorder_recommendation,
)
from apps.promotion_committee.models import (
    AdoptionActionRecommendation,
    AdoptionActionRecommendationType,
    AdoptionRollbackPlan,
    ManualAdoptionAction,
    ManualAdoptionActionStatus,
    ManualAdoptionActionType,
    PromotionAdoptionRun,
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


@transaction.atomic
def run_promotion_adoption_review(*, actor: str = 'promotion_ui', metadata: dict | None = None):
    latest_review_run = PromotionReviewCycleRun.objects.order_by('-started_at', '-id').first()
    adoption_run = PromotionAdoptionRun.objects.create(
        started_at=timezone.now(),
        linked_promotion_review_run=latest_review_run,
        metadata={'actor': actor, 'manual_first': True, **(metadata or {})},
    )
    candidates = build_adoption_candidates(adoption_run=adoption_run)

    recommendation_counter = Counter()
    for candidate in candidates:
        action, needs_rollback = plan_manual_action(adoption_run=adoption_run, candidate=candidate)
        if needs_rollback:
            prepare_rollback_plan(action=action)
        create_adoption_recommendation(adoption_run=adoption_run, action=action, needs_rollback=needs_rollback)

    recommendation_counter.update(
        AdoptionActionRecommendation.objects.filter(adoption_run=adoption_run).values_list('recommendation_type', flat=True)
    )
    actions = ManualAdoptionAction.objects.filter(adoption_run=adoption_run)

    adoption_run.candidate_count = len(candidates)
    adoption_run.ready_to_apply_count = actions.filter(action_status=ManualAdoptionActionStatus.READY_TO_APPLY).count()
    adoption_run.blocked_count = actions.filter(action_status=ManualAdoptionActionStatus.BLOCKED).count()
    adoption_run.applied_count = actions.filter(action_status=ManualAdoptionActionStatus.APPLIED).count()
    adoption_run.rollback_plan_count = AdoptionRollbackPlan.objects.filter(linked_manual_action__adoption_run=adoption_run).count()
    adoption_run.rollout_handoff_count = actions.filter(action_type=ManualAdoptionActionType.PREPARE_ROLLOUT_PLAN).count()
    adoption_run.recommendation_summary = dict(recommendation_counter)
    adoption_run.completed_at = timezone.now()
    adoption_run.save(
        update_fields=[
            'candidate_count',
            'ready_to_apply_count',
            'blocked_count',
            'applied_count',
            'rollback_plan_count',
            'rollout_handoff_count',
            'recommendation_summary',
            'completed_at',
            'updated_at',
        ]
    )
    return adoption_run


def build_adoption_summary():
    latest = PromotionAdoptionRun.objects.order_by('-started_at', '-id').first()
    approved_cases = PromotionCase.objects.filter(case_status=PromotionCaseStatus.APPROVED_FOR_MANUAL_ADOPTION).count()
    return {
        'latest_run': latest,
        'approved_cases': approved_cases,
        'ready_to_apply': latest.ready_to_apply_count if latest else 0,
        'blocked': latest.blocked_count if latest else 0,
        'applied': latest.applied_count if latest else 0,
        'rollback_prepared': latest.rollback_plan_count if latest else 0,
        'rollout_handoff_ready': latest.rollout_handoff_count if latest else 0,
        'recommendation_summary': latest.recommendation_summary if latest else {},
    }

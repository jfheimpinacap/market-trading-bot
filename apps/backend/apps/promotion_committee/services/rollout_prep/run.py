from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.promotion_committee.models import (
    ManualRollbackExecution,
    ManualRollbackExecutionStatus,
    ManualRolloutPlan,
    ManualRolloutPlanStatus,
    PromotionAdoptionRun,
    RolloutCheckpointPlan,
    RolloutPreparationRun,
)
from apps.promotion_committee.services.rollout_prep.candidate_building import build_rollout_candidates
from apps.promotion_committee.services.rollout_prep.checkpoints import prepare_checkpoint_plans
from apps.promotion_committee.services.rollout_prep.recommendation import create_rollout_recommendations
from apps.promotion_committee.services.rollout_prep.rollback_execution import prepare_manual_rollback_execution
from apps.promotion_committee.services.rollout_prep.rollout_planning import plan_manual_rollout


@transaction.atomic
def run_rollout_preparation(*, actor: str = 'promotion_ui', metadata: dict | None = None):
    latest_adoption_run = PromotionAdoptionRun.objects.order_by('-started_at', '-id').first()
    run = RolloutPreparationRun.objects.create(
        started_at=timezone.now(),
        linked_adoption_run=latest_adoption_run,
        metadata={'actor': actor, 'manual_first': True, 'paper_only': True, **(metadata or {})},
    )

    candidates = build_rollout_candidates(preparation_run=run)

    for candidate in candidates:
        plan = plan_manual_rollout(candidate=candidate)
        prepare_checkpoint_plans(plan=plan)
        rollback_execution = prepare_manual_rollback_execution(action=candidate.linked_manual_adoption_action, plan=plan)
        create_rollout_recommendations(
            preparation_run=run,
            candidate=candidate,
            plan=plan,
            rollback_execution=rollback_execution,
        )

    recommendation_counter = Counter(run.rollout_recommendations.values_list('recommendation_type', flat=True))

    run.candidate_count = len(candidates)
    run.rollout_ready_count = ManualRolloutPlan.objects.filter(linked_candidate__preparation_run=run, rollout_status=ManualRolloutPlanStatus.READY).count()
    run.blocked_count = ManualRolloutPlan.objects.filter(linked_candidate__preparation_run=run, rollout_status=ManualRolloutPlanStatus.BLOCKED).count()
    run.checkpoint_count = RolloutCheckpointPlan.objects.filter(linked_rollout_plan__linked_candidate__preparation_run=run).count()
    run.rollback_ready_count = ManualRollbackExecution.objects.filter(
        linked_manual_action__rollout_candidate__preparation_run=run,
        execution_status=ManualRollbackExecutionStatus.READY,
    ).count()
    run.rollback_executed_count = ManualRollbackExecution.objects.filter(
        linked_manual_action__rollout_candidate__preparation_run=run,
        execution_status=ManualRollbackExecutionStatus.EXECUTED,
    ).count()
    run.recommendation_summary = dict(recommendation_counter)
    run.completed_at = timezone.now()
    run.save(
        update_fields=[
            'candidate_count',
            'rollout_ready_count',
            'blocked_count',
            'checkpoint_count',
            'rollback_ready_count',
            'rollback_executed_count',
            'recommendation_summary',
            'completed_at',
            'updated_at',
        ]
    )
    return run


def build_rollout_preparation_summary():
    latest = RolloutPreparationRun.objects.order_by('-started_at', '-id').first()
    return {
        'latest_run': latest,
        'candidates': latest.candidate_count if latest else 0,
        'ready': latest.rollout_ready_count if latest else 0,
        'blocked': latest.blocked_count if latest else 0,
        'checkpoint_plans': latest.checkpoint_count if latest else 0,
        'rollback_ready': latest.rollback_ready_count if latest else 0,
        'rollback_executed': latest.rollback_executed_count if latest else 0,
        'recommendation_summary': latest.recommendation_summary if latest else {},
    }

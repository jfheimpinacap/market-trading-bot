from __future__ import annotations

from django.utils import timezone

from apps.promotion_committee.models import (
    ManualRollbackExecution,
    ManualRollbackExecutionStatus,
    RolloutExecutionRun,
    RolloutExecutionStatus,
    RolloutPreparationRun,
)
from apps.promotion_committee.services.rollout_execution.execution import register_rollout_execution_records
from apps.promotion_committee.services.rollout_execution.recommendation import generate_execution_recommendations


def run_rollout_execution_review(*, actor: str = 'promotion_ui', metadata: dict | None = None) -> RolloutExecutionRun:
    latest_prep = RolloutPreparationRun.objects.order_by('-started_at', '-id').first()
    run = RolloutExecutionRun.objects.create(
        started_at=timezone.now(),
        linked_rollout_preparation_run=latest_prep,
        metadata={'actor': actor, 'manual_first': True, 'paper_only': True, **(metadata or {})},
    )

    records = register_rollout_execution_records(run=run)
    run.plan_count = len(records)
    run.executed_count = sum(1 for item in records if item.execution_status == RolloutExecutionStatus.EXECUTED)
    run.paused_count = sum(1 for item in records if item.execution_status == RolloutExecutionStatus.PAUSED)
    run.failed_count = sum(1 for item in records if item.execution_status == RolloutExecutionStatus.FAILED)
    run.rollback_recommended_count = sum(
        1 for item in records if item.execution_status == RolloutExecutionStatus.ROLLBACK_RECOMMENDED
    )
    run.rollback_executed_count = ManualRollbackExecution.objects.filter(
        linked_rollout_plan__execution_record__execution_run=run,
        execution_status=ManualRollbackExecutionStatus.EXECUTED,
    ).count()
    run.completed_at = timezone.now()
    run.save(
        update_fields=[
            'plan_count',
            'executed_count',
            'paused_count',
            'failed_count',
            'rollback_recommended_count',
            'rollback_executed_count',
            'completed_at',
            'updated_at',
        ]
    )

    generate_execution_recommendations(run=run)
    return run


def build_rollout_execution_summary() -> dict:
    latest = RolloutExecutionRun.objects.order_by('-started_at', '-id').first()
    return {
        'latest_run': latest,
        'rollout_plans_ready': latest.plan_count if latest else 0,
        'executions_running': latest.paused_count if latest else 0,
        'healthy_rollouts': latest.execution_records.filter(post_rollout_statuses__status='HEALTHY').distinct().count() if latest else 0,
        'review_required': latest.execution_records.filter(post_rollout_statuses__status='REVIEW_REQUIRED').distinct().count() if latest else 0,
        'rollback_recommended': latest.rollback_recommended_count if latest else 0,
        'rollback_executed': latest.rollback_executed_count if latest else 0,
        'recommendation_summary': latest.recommendation_summary if latest else {},
    }

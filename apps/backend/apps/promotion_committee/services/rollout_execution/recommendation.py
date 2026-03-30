from __future__ import annotations

from collections import Counter
from decimal import Decimal

from apps.promotion_committee.models import (
    PostRolloutStatus,
    PostRolloutStatusType,
    RolloutExecutionRecommendation,
    RolloutExecutionRecommendationType,
    RolloutExecutionRun,
    RolloutExecutionStatus,
)


def generate_execution_recommendations(*, run: RolloutExecutionRun) -> list[RolloutExecutionRecommendation]:
    run.execution_recommendations.all().delete()
    created: list[RolloutExecutionRecommendation] = []
    for execution in run.execution_records.select_related('linked_rollout_plan').all():
        latest_status = PostRolloutStatus.objects.filter(linked_rollout_execution=execution).order_by('-created_at', '-id').first()

        if execution.execution_status == RolloutExecutionStatus.READY:
            rec_type = RolloutExecutionRecommendationType.EXECUTE_NEXT_STAGE
            rationale = 'Plan is ready and waiting for explicit manual execution.'
            confidence = Decimal('0.8800')
            reason_codes = ['ready_for_manual_execute']
            blockers = list(execution.blockers or [])
        elif execution.execution_status in {RolloutExecutionStatus.PAUSED, RolloutExecutionStatus.FAILED}:
            rec_type = RolloutExecutionRecommendationType.PAUSE_AND_REVIEW
            rationale = 'Execution is paused/failed and requires operator review before continuing.'
            confidence = Decimal('0.9100')
            reason_codes = ['paused_or_failed']
            blockers = list(execution.blockers or [])
        elif execution.execution_status == RolloutExecutionStatus.ROLLBACK_RECOMMENDED or (
            latest_status and latest_status.status == PostRolloutStatusType.ROLLBACK_RECOMMENDED
        ):
            rec_type = RolloutExecutionRecommendationType.RECOMMEND_MANUAL_ROLLBACK
            rationale = 'Checkpoint evidence suggests manual rollback path should be executed.'
            confidence = Decimal('0.9400')
            reason_codes = ['critical_checkpoint_failure']
            blockers = []
        elif latest_status and latest_status.status == PostRolloutStatusType.HEALTHY:
            rec_type = RolloutExecutionRecommendationType.CLOSE_ROLLOUT
            rationale = 'Post-rollout status is healthy; execution can be manually closed.'
            confidence = Decimal('0.8600')
            reason_codes = ['healthy_post_rollout']
            blockers = []
        elif latest_status and latest_status.status == PostRolloutStatusType.CAUTION:
            rec_type = RolloutExecutionRecommendationType.REQUIRE_MORE_OBSERVATION
            rationale = 'Warning-level signals present; collect more bounded observations before closure.'
            confidence = Decimal('0.7800')
            reason_codes = ['warning_observed']
            blockers = []
        else:
            rec_type = RolloutExecutionRecommendationType.MARK_ROLLOUT_HEALTHY
            rationale = 'No critical blockers; maintain manual monitoring and mark healthy when confirmed.'
            confidence = Decimal('0.7200')
            reason_codes = ['manual_monitoring_continues']
            blockers = []

        created.append(
            RolloutExecutionRecommendation.objects.create(
                execution_run=run,
                target_execution=execution,
                recommendation_type=rec_type,
                rationale=rationale,
                reason_codes=reason_codes,
                confidence=confidence,
                blockers=blockers,
                metadata={'manual_only': True},
            )
        )

    summary = Counter([item.recommendation_type for item in created])
    run.recommendation_summary = dict(summary)
    run.save(update_fields=['recommendation_summary', 'updated_at'])
    return created

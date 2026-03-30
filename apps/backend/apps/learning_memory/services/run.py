from __future__ import annotations

from django.utils import timezone

from apps.learning_memory.models import (
    FailurePattern,
    FailurePatternStatus,
    LoopAdjustmentStatus,
    PostmortemLearningAdjustment,
    PostmortemLearningRun,
)
from apps.learning_memory.services.adjustments_loop import derive_adjustments_from_patterns
from apps.postmortem_agents.models import PostmortemBoardRun
from apps.learning_memory.services.application import record_default_loop_applications
from apps.learning_memory.services.patterns import derive_patterns_from_postmortem
from apps.learning_memory.services.recommendation import rebuild_recommendations


def run_postmortem_learning_loop(*, linked_postmortem_run_id: int | None = None) -> PostmortemLearningRun:
    started_at = timezone.now()
    run = PostmortemLearningRun.objects.create(
        linked_postmortem_run_id=linked_postmortem_run_id,
        started_at=started_at,
        metadata={'mode': 'manual_first_recommendation_first'},
    )

    derived = derive_patterns_from_postmortem(board_run_id=linked_postmortem_run_id)
    derive_adjustments_from_patterns(patterns=[item.pattern for item in derived])
    applications_count = record_default_loop_applications()
    recommendations = rebuild_recommendations()

    active_adjustments = PostmortemLearningAdjustment.objects.filter(status=LoopAdjustmentStatus.ACTIVE).count()
    expired_adjustments = PostmortemLearningAdjustment.objects.filter(status=LoopAdjustmentStatus.EXPIRED).count()
    reviewed_positions = PostmortemBoardRun.objects.filter(status='SUCCESS').count()

    run.completed_at = timezone.now()
    run.reviewed_position_count = reviewed_positions
    run.failure_pattern_count = FailurePattern.objects.count()
    run.adjustment_count = PostmortemLearningAdjustment.objects.count()
    run.active_adjustment_count = active_adjustments
    run.expired_adjustment_count = expired_adjustments
    run.recommendation_summary = f'Recommendations={len(recommendations)} applications={applications_count}.'
    run.metadata = {
        **(run.metadata or {}),
        'patterns_active': FailurePattern.objects.filter(status=FailurePatternStatus.ACTIVE).count(),
        'patterns_watch': FailurePattern.objects.filter(status=FailurePatternStatus.WATCH).count(),
        'applications_recorded_this_run': applications_count,
    }
    run.save(
        update_fields=[
            'completed_at',
            'reviewed_position_count',
            'failure_pattern_count',
            'adjustment_count',
            'active_adjustment_count',
            'expired_adjustment_count',
            'recommendation_summary',
            'metadata',
            'updated_at',
        ]
    )
    return run

from __future__ import annotations

from decimal import Decimal

from apps.learning_memory.models import (
    LearningRecommendation,
    LearningRecommendationType,
    LoopAdjustmentStatus,
    PostmortemLearningAdjustment,
)


def rebuild_recommendations() -> list[LearningRecommendation]:
    LearningRecommendation.objects.all().delete()
    created: list[LearningRecommendation] = []

    active = list(PostmortemLearningAdjustment.objects.filter(status=LoopAdjustmentStatus.ACTIVE).order_by('-updated_at', '-id'))
    proposed = list(PostmortemLearningAdjustment.objects.filter(status=LoopAdjustmentStatus.PROPOSED).order_by('-updated_at', '-id')[:20])
    expired = list(PostmortemLearningAdjustment.objects.filter(status=LoopAdjustmentStatus.EXPIRED).order_by('-updated_at', '-id')[:20])

    for adjustment in active[:10]:
        created.append(
            LearningRecommendation.objects.create(
                recommendation_type=LearningRecommendationType.ATTACH_CAUTION_TO_RISK,
                target_adjustment=adjustment,
                rationale='Active conservative adjustment should be visible in risk and proposal review.',
                reason_codes=['ACTIVE_ADJUSTMENT', adjustment.adjustment_type.upper()],
                confidence=Decimal('0.8200'),
                blockers=[],
            )
        )

    for adjustment in proposed[:10]:
        rec_type = LearningRecommendationType.KEEP_ADJUSTMENT_ON_WATCH
        if adjustment.adjustment_strength >= Decimal('0.1100'):
            rec_type = LearningRecommendationType.ACTIVATE_ADJUSTMENT
        created.append(
            LearningRecommendation.objects.create(
                recommendation_type=rec_type,
                target_adjustment=adjustment,
                target_pattern=adjustment.linked_failure_pattern,
                rationale='Bounded recommendation derived from recurrence and severity.',
                reason_codes=['STATUS_PROPOSED', f'STR_{adjustment.adjustment_strength}'],
                confidence=Decimal('0.6800'),
                blockers=[] if rec_type == LearningRecommendationType.ACTIVATE_ADJUSTMENT else ['NEEDS_RECURRENCE_CONFIRMATION'],
            )
        )

    for adjustment in expired[:5]:
        created.append(
            LearningRecommendation.objects.create(
                recommendation_type=LearningRecommendationType.EXPIRE_ADJUSTMENT,
                target_adjustment=adjustment,
                rationale='Adjustment has aged without strong recent evidence.',
                reason_codes=['STALE_ADJUSTMENT'],
                confidence=Decimal('0.7400'),
                blockers=[],
            )
        )

    if len(active) >= 8:
        created.append(
            LearningRecommendation.objects.create(
                recommendation_type=LearningRecommendationType.REORDER_LEARNING_PRIORITY,
                rationale='Too many active adjustments can over-constrain the next decision.',
                reason_codes=['ACTIVE_ADJUSTMENT_OVERLOAD'],
                confidence=Decimal('0.7600'),
                blockers=['REQUIRES_MANUAL_CURATION'],
            )
        )
        created.append(
            LearningRecommendation.objects.create(
                recommendation_type=LearningRecommendationType.REQUIRE_MANUAL_LEARNING_REVIEW,
                rationale='Manual review required when active adjustments exceed conservative threshold.',
                reason_codes=['MANUAL_REVIEW_GUARDRAIL'],
                confidence=Decimal('0.9100'),
                blockers=[],
            )
        )

    return created

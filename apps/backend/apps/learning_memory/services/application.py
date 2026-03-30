from __future__ import annotations

from decimal import Decimal

from apps.learning_memory.models import (
    LearningApplicationRecord,
    LearningApplicationTarget,
    LearningApplicationType,
    LoopAdjustmentStatus,
    LoopAdjustmentType,
    PostmortemLearningAdjustment,
)


def record_application_for_component(*, target_component: str, target_entity_id: str = '', max_records: int = 3) -> int:
    active_adjustments = PostmortemLearningAdjustment.objects.filter(status=LoopAdjustmentStatus.ACTIVE).order_by('-updated_at', '-id')[:max_records]
    created = 0
    for adjustment in active_adjustments:
        app_type = LearningApplicationType.CAUTION_ATTACHED
        before_value = ''
        after_value = ''
        if adjustment.adjustment_type in {LoopAdjustmentType.CONFIDENCE_PENALTY, LoopAdjustmentType.EDGE_PENALTY, LoopAdjustmentType.LIQUIDITY_PENALTY}:
            app_type = LearningApplicationType.SCORE_PENALTY_APPLIED
            before_value = '1.0000'
            after_value = str(max(Decimal('0.6000'), Decimal('1.0000') - adjustment.adjustment_strength))
        elif adjustment.adjustment_type == LoopAdjustmentType.RISK_SIZE_CAP:
            app_type = LearningApplicationType.SIZE_CAP_APPLIED
            before_value = '1.0000'
            after_value = str(max(Decimal('0.5000'), Decimal('1.0000') - adjustment.adjustment_strength))
        elif adjustment.adjustment_type == LoopAdjustmentType.MANUAL_REVIEW_TRIGGER:
            app_type = LearningApplicationType.MANUAL_REVIEW_REQUIRED

        LearningApplicationRecord.objects.create(
            linked_adjustment=adjustment,
            target_component=target_component,
            target_entity_id=str(target_entity_id or ''),
            application_type=app_type,
            before_value=before_value,
            after_value=after_value,
            rationale=f'Applied conservative learning adjustment for {target_component}.',
            metadata={'source': 'postmortem_learning_loop'},
        )
        created += 1
    return created


def record_default_loop_applications() -> int:
    total = 0
    for component in [
        LearningApplicationTarget.PREDICTION,
        LearningApplicationTarget.RISK,
        LearningApplicationTarget.PROPOSAL,
        LearningApplicationTarget.SIGNAL_FUSION,
    ]:
        total += record_application_for_component(target_component=component, target_entity_id='loop-preview', max_records=2)
    return total

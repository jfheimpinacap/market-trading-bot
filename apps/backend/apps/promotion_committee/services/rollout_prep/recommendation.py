from __future__ import annotations

from decimal import Decimal

from apps.promotion_committee.models import (
    ManualRollbackExecution,
    ManualRollbackExecutionStatus,
    ManualRolloutPlan,
    RolloutActionCandidate,
    RolloutNeedLevel,
    RolloutPreparationRecommendation,
    RolloutPreparationRecommendationType,
    RolloutPreparationRun,
)


def create_rollout_recommendations(
    *,
    preparation_run: RolloutPreparationRun,
    candidate: RolloutActionCandidate,
    plan: ManualRolloutPlan,
    rollback_execution: ManualRollbackExecution,
) -> list[RolloutPreparationRecommendation]:
    created: list[RolloutPreparationRecommendation] = []

    if candidate.rollout_need_level == RolloutNeedLevel.DIRECT_APPLY_OK:
        rec_type = RolloutPreparationRecommendationType.DIRECT_APPLY_OK
        rationale = 'Bounded change can be manually applied without staged rollout.'
        confidence = Decimal('0.8100')
    elif candidate.rollout_need_level == RolloutNeedLevel.ROLLOUT_REQUIRED:
        rec_type = RolloutPreparationRecommendationType.PREPARE_MANUAL_ROLLOUT
        rationale = 'Sensitive/global change requires explicit staged manual rollout plan.'
        confidence = Decimal('0.9200')
    else:
        rec_type = RolloutPreparationRecommendationType.REQUIRE_ROLLOUT_CHECKPOINTS
        rationale = 'Change should include monitoring checkpoints before manual apply.'
        confidence = Decimal('0.8600')

    created.append(
        RolloutPreparationRecommendation.objects.create(
            preparation_run=preparation_run,
            target_candidate=candidate,
            target_plan=plan,
            recommendation_type=rec_type,
            rationale=rationale,
            reason_codes=list(candidate.metadata.get('reason_codes', [])),
            confidence=confidence,
            blockers=list(candidate.blockers or []),
            metadata={'manual_only': True},
        )
    )

    if candidate.target_resolution_status in {'BLOCKED', 'UNKNOWN', 'PARTIAL'}:
        created.append(
            RolloutPreparationRecommendation.objects.create(
                preparation_run=preparation_run,
                target_candidate=candidate,
                target_plan=plan,
                recommendation_type=RolloutPreparationRecommendationType.REQUIRE_TARGET_RECHECK,
                rationale='Target mapping must be rechecked before any rollout execution step.',
                reason_codes=['target_mapping_incomplete'],
                confidence=Decimal('0.9400'),
                blockers=list(candidate.blockers or []),
                metadata={'manual_only': True},
            )
        )

    if rollback_execution.execution_status == ManualRollbackExecutionStatus.READY:
        created.append(
            RolloutPreparationRecommendation.objects.create(
                preparation_run=preparation_run,
                target_candidate=candidate,
                target_plan=plan,
                recommendation_type=RolloutPreparationRecommendationType.ROLLBACK_READY,
                rationale='Rollback execution path is prepared and manually triggerable.',
                reason_codes=['rollback_prepared'],
                confidence=Decimal('0.8900'),
                blockers=[],
                metadata={'manual_only': True},
            )
        )

    return created

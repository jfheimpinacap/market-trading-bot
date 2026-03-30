from __future__ import annotations

from apps.promotion_committee.models import (
    ManualRolloutPlan,
    RolloutCheckpointPlan,
    RolloutCheckpointType,
    RolloutNeedLevel,
)


def _checkpoint_types(plan: ManualRolloutPlan) -> list[str]:
    types = [RolloutCheckpointType.PRE_APPLY_CHECK, RolloutCheckpointType.ROLLBACK_READINESS_CHECK]
    if plan.rollout_plan_type != 'DIRECT_CONFIG_APPLY':
        types += [RolloutCheckpointType.PROPOSAL_QUALITY_CHECK, RolloutCheckpointType.POST_APPLY_CHECK]
    if plan.target_component in {'calibration', 'prediction'}:
        types.append(RolloutCheckpointType.CALIBRATION_CHECK)
    if plan.target_component == 'risk':
        types.append(RolloutCheckpointType.RISK_GATE_CHECK)
    if plan.linked_candidate.rollout_need_level in {RolloutNeedLevel.ROLLOUT_RECOMMENDED, RolloutNeedLevel.ROLLOUT_REQUIRED}:
        types.append(RolloutCheckpointType.METRIC_DRIFT_CHECK)
    return types


def prepare_checkpoint_plans(*, plan: ManualRolloutPlan) -> list[RolloutCheckpointPlan]:
    existing = set(plan.checkpoint_plans.values_list('checkpoint_type', flat=True))
    created: list[RolloutCheckpointPlan] = []
    for checkpoint_type in _checkpoint_types(plan):
        if checkpoint_type in existing:
            continue
        created.append(
            RolloutCheckpointPlan.objects.create(
                linked_rollout_plan=plan,
                checkpoint_type=checkpoint_type,
                checkpoint_status='PLANNED',
                checkpoint_rationale=f'{checkpoint_type} required for explicit auditable manual rollout.',
                metadata={'manual_gate': True},
            )
        )
    return created

from __future__ import annotations

from apps.mission_control.models import (
    AutonomousMissionCyclePlan,
    AutonomousMissionCyclePlanStatus,
    AutonomousMissionRecommendationType,
    AutonomousMissionRuntimeRecommendation,
    AutonomousMissionRuntimeRun,
)


def emit_recommendation(*, runtime_run: AutonomousMissionRuntimeRun, cycle_plan: AutonomousMissionCyclePlan | None = None) -> AutonomousMissionRuntimeRecommendation:
    blockers: list[str] = []
    reason_codes: list[str] = []

    if cycle_plan and cycle_plan.plan_status == AutonomousMissionCyclePlanStatus.BLOCKED:
        recommendation_type = AutonomousMissionRecommendationType.PAUSE_FOR_SAFETY_OR_RUNTIME_BLOCK
        blockers = list(cycle_plan.reason_codes or ['blocked'])
        reason_codes = blockers
        rationale = 'Cycle planning detected a hard block from runtime/safety guardrails.'
        confidence = 0.95
    elif cycle_plan and cycle_plan.plan_status == AutonomousMissionCyclePlanStatus.REDUCED:
        recommendation_type = AutonomousMissionRecommendationType.RUN_REDUCED_CYCLE
        reason_codes = list(cycle_plan.reason_codes or ['reduced'])
        rationale = 'Cycle should run in reduced mode due to posture/degraded constraints.'
        confidence = 0.8
    else:
        recommendation_type = AutonomousMissionRecommendationType.RUN_FULL_CYCLE
        rationale = 'Guardrails allow full paper-only cycle orchestration.'
        confidence = 0.75

    return AutonomousMissionRuntimeRecommendation.objects.create(
        recommendation_type=recommendation_type,
        target_runtime_run=runtime_run,
        target_cycle_plan=cycle_plan,
        rationale=rationale,
        reason_codes=reason_codes,
        confidence=confidence,
        blockers=blockers,
    )

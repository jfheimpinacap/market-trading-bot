from __future__ import annotations

from apps.runtime_governor.models import (
    GlobalModeEnforcementDecision,
    GlobalModeEnforcementDecisionStatus,
    GlobalModeEnforcementDecisionType,
    GlobalModeImpactStatus,
)


DECISION_BY_MODULE = {
    'timing_policy': GlobalModeEnforcementDecisionType.REDUCE_CADENCE,
    'session_admission': GlobalModeEnforcementDecisionType.REDUCE_ADMISSION_CAPACITY,
    'exposure_coordination': GlobalModeEnforcementDecisionType.THROTTLE_EXPOSURE,
    'exposure_apply': GlobalModeEnforcementDecisionType.REQUIRE_MANUAL_REVIEW_BIAS,
    'execution_intake': GlobalModeEnforcementDecisionType.BLOCK_NEW_EXECUTION,
    'heartbeat_runner': GlobalModeEnforcementDecisionType.FORCE_MONITOR_ONLY,
    'session_recovery': GlobalModeEnforcementDecisionType.REQUIRE_MANUAL_REVIEW_BIAS,
}


def apply_module_enforcement(*, enforcement_run, impacts: list) -> list[GlobalModeEnforcementDecision]:
    decisions: list[GlobalModeEnforcementDecision] = []
    for impact in impacts:
        if impact.impact_status == GlobalModeImpactStatus.UNCHANGED:
            decision_type = GlobalModeEnforcementDecisionType.KEEP_DEFAULT_BEHAVIOR
            decision_status = GlobalModeEnforcementDecisionStatus.SKIPPED
        else:
            decision_type = DECISION_BY_MODULE.get(impact.module_name, GlobalModeEnforcementDecisionType.REQUIRE_MANUAL_REVIEW_BIAS)
            decision_status = GlobalModeEnforcementDecisionStatus.APPLIED
            if impact.impact_status == GlobalModeImpactStatus.BLOCKED:
                decision_status = GlobalModeEnforcementDecisionStatus.BLOCKED
        decision = GlobalModeEnforcementDecision.objects.create(
            linked_enforcement_run=enforcement_run,
            module_name=impact.module_name,
            decision_type=decision_type,
            decision_status=decision_status,
            auto_applicable=decision_status != GlobalModeEnforcementDecisionStatus.BLOCKED,
            decision_summary=impact.effective_behavior_summary,
            reason_codes=impact.reason_codes,
            metadata={'impact_status': impact.impact_status, **(impact.metadata or {})},
        )
        decisions.append(decision)
    return decisions


def build_downstream_enforcement_summary(*, current_mode: str, decisions: list[GlobalModeEnforcementDecision], impacts: list) -> dict:
    return {
        'current_mode': current_mode,
        'module_impacts': [
            {
                'module_name': impact.module_name,
                'impact_status': impact.impact_status,
                'summary': impact.effective_behavior_summary,
            }
            for impact in impacts
        ],
        'enforcement_decisions': [
            {
                'module_name': d.module_name,
                'decision_type': d.decision_type,
                'decision_status': d.decision_status,
            }
            for d in decisions
        ],
    }

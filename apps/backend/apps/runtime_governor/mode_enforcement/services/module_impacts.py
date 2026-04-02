from __future__ import annotations

from apps.runtime_governor.models import (
    GlobalModeEnforcementEffectType,
    GlobalModeImpactStatus,
    GlobalModeModuleImpact,
)
from apps.runtime_governor.mode_enforcement.services.rules import GlobalModeEnforcementRule


IMPACT_MAP = {
    GlobalModeEnforcementEffectType.NO_CHANGE: GlobalModeImpactStatus.UNCHANGED,
    GlobalModeEnforcementEffectType.SOFT_REDUCTION: GlobalModeImpactStatus.REDUCED,
    GlobalModeEnforcementEffectType.THROTTLE: GlobalModeImpactStatus.THROTTLED,
    GlobalModeEnforcementEffectType.MONITOR_ONLY: GlobalModeImpactStatus.MONITOR_ONLY,
    GlobalModeEnforcementEffectType.BLOCK_NEW_ACTIVITY: GlobalModeImpactStatus.BLOCKED,
    GlobalModeEnforcementEffectType.MANUAL_REVIEW_BIAS: GlobalModeImpactStatus.REDUCED,
}


def build_module_impacts(*, enforcement_run, current_mode: str, rules: list[GlobalModeEnforcementRule]) -> list[GlobalModeModuleImpact]:
    impacts: list[GlobalModeModuleImpact] = []
    for rule in rules:
        impact = GlobalModeModuleImpact.objects.create(
            linked_enforcement_run=enforcement_run,
            current_mode=current_mode,
            module_name=rule.module_name,
            impact_status=IMPACT_MAP[rule.effect_type],
            effective_behavior_summary=rule.rule_summary,
            reason_codes=rule.reason_codes,
            metadata={
                'effect_type': rule.effect_type,
                **(rule.metadata or {}),
            },
        )
        impacts.append(impact)
    return impacts

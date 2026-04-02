from __future__ import annotations

from dataclasses import dataclass

from apps.runtime_governor.models import GlobalModeEnforcementEffectType, GlobalOperatingMode


MODULES = (
    'timing_policy',
    'session_admission',
    'exposure_coordination',
    'exposure_apply',
    'execution_intake',
    'heartbeat_runner',
    'session_recovery',
)


@dataclass(frozen=True)
class GlobalModeEnforcementRule:
    mode: str
    module_name: str
    effect_type: str
    rule_summary: str
    reason_codes: list[str]
    metadata: dict


_RULES: dict[str, dict[str, GlobalModeEnforcementRule]] = {
    GlobalOperatingMode.BALANCED: {
        module: GlobalModeEnforcementRule(
            mode=GlobalOperatingMode.BALANCED,
            module_name=module,
            effect_type=GlobalModeEnforcementEffectType.NO_CHANGE,
            rule_summary='Balanced mode keeps default conservative paper-only behavior.',
            reason_codes=['mode:balanced', f'module:{module}', 'effect:no_change'],
            metadata={'intensity_factor': 1.0},
        )
        for module in MODULES
    },
    GlobalOperatingMode.CAUTION: {
        'timing_policy': GlobalModeEnforcementRule(GlobalOperatingMode.CAUTION, 'timing_policy', GlobalModeEnforcementEffectType.SOFT_REDUCTION, 'Reduce cadence and increase quiet-window bias.', ['mode:caution', 'reduce_cadence'], {'cadence_factor': 0.75}),
        'session_admission': GlobalModeEnforcementRule(GlobalOperatingMode.CAUTION, 'session_admission', GlobalModeEnforcementEffectType.SOFT_REDUCTION, 'Reduce admission/resume capacity and favor conservative admission.', ['mode:caution', 'admission_conservative'], {'admission_factor': 0.7}),
        'exposure_coordination': GlobalModeEnforcementRule(GlobalOperatingMode.CAUTION, 'exposure_coordination', GlobalModeEnforcementEffectType.SOFT_REDUCTION, 'Bias toward lower concentration and conservative exposure limits.', ['mode:caution', 'exposure_soft_reduction'], {'exposure_factor': 0.8}),
        'exposure_apply': GlobalModeEnforcementRule(GlobalOperatingMode.CAUTION, 'exposure_apply', GlobalModeEnforcementEffectType.MANUAL_REVIEW_BIAS, 'Apply exposure with stronger manual review bias for marginal expansions.', ['mode:caution', 'manual_review_bias'], {'manual_review_bias': True}),
        'execution_intake': GlobalModeEnforcementRule(GlobalOperatingMode.CAUTION, 'execution_intake', GlobalModeEnforcementEffectType.SOFT_REDUCTION, 'Reduce autonomous execution intake throughput.', ['mode:caution', 'execution_soft_reduction'], {'execution_intake_factor': 0.7}),
        'heartbeat_runner': GlobalModeEnforcementRule(GlobalOperatingMode.CAUTION, 'heartbeat_runner', GlobalModeEnforcementEffectType.SOFT_REDUCTION, 'Heartbeat remains active with reduced intensity.', ['mode:caution', 'heartbeat_reduced'], {'heartbeat_factor': 0.8}),
        'session_recovery': GlobalModeEnforcementRule(GlobalOperatingMode.CAUTION, 'session_recovery', GlobalModeEnforcementEffectType.MANUAL_REVIEW_BIAS, 'Favor conservative resume/recovery checks before re-entry.', ['mode:caution', 'recovery_review_bias'], {'resume_gate': 'strict'}),
    },
    GlobalOperatingMode.MONITOR_ONLY: {
        module: GlobalModeEnforcementRule(GlobalOperatingMode.MONITOR_ONLY, module, GlobalModeEnforcementEffectType.MONITOR_ONLY if module in {'timing_policy', 'session_admission', 'heartbeat_runner', 'session_recovery'} else GlobalModeEnforcementEffectType.BLOCK_NEW_ACTIVITY, 'Monitor-only posture blocks net-new operational activity and keeps observation/health loops.', ['mode:monitor_only', f'module:{module}'], {'monitor_only': True})
        for module in MODULES
    },
    GlobalOperatingMode.RECOVERY_MODE: {
        'timing_policy': GlobalModeEnforcementRule(GlobalOperatingMode.RECOVERY_MODE, 'timing_policy', GlobalModeEnforcementEffectType.SOFT_REDUCTION, 'Increase wait windows while recovering stability.', ['mode:recovery', 'cadence_long_wait'], {'cadence_factor': 0.6}),
        'session_admission': GlobalModeEnforcementRule(GlobalOperatingMode.RECOVERY_MODE, 'session_admission', GlobalModeEnforcementEffectType.THROTTLE, 'Throttle new admissions; prioritize recovered sessions only.', ['mode:recovery', 'admission_throttle'], {'admission_factor': 0.5}),
        'exposure_coordination': GlobalModeEnforcementRule(GlobalOperatingMode.RECOVERY_MODE, 'exposure_coordination', GlobalModeEnforcementEffectType.THROTTLE, 'Throttle exposure expansion until losses stabilize.', ['mode:recovery', 'exposure_throttle'], {'exposure_factor': 0.55}),
        'exposure_apply': GlobalModeEnforcementRule(GlobalOperatingMode.RECOVERY_MODE, 'exposure_apply', GlobalModeEnforcementEffectType.MANUAL_REVIEW_BIAS, 'Bias exposure apply toward manual review when adding risk.', ['mode:recovery', 'manual_review_bias'], {'manual_review_bias': True}),
        'execution_intake': GlobalModeEnforcementRule(GlobalOperatingMode.RECOVERY_MODE, 'execution_intake', GlobalModeEnforcementEffectType.BLOCK_NEW_ACTIVITY, 'Block new autonomous execution intake while recovering.', ['mode:recovery', 'block_execution_intake'], {'allow_new_execution': False}),
        'heartbeat_runner': GlobalModeEnforcementRule(GlobalOperatingMode.RECOVERY_MODE, 'heartbeat_runner', GlobalModeEnforcementEffectType.SOFT_REDUCTION, 'Keep heartbeat active at low intensity focused on health and recovery.', ['mode:recovery', 'heartbeat_recovery_bias'], {'heartbeat_factor': 0.7}),
        'session_recovery': GlobalModeEnforcementRule(GlobalOperatingMode.RECOVERY_MODE, 'session_recovery', GlobalModeEnforcementEffectType.MONITOR_ONLY, 'Recovery subsystem runs in conservative monitor-first mode.', ['mode:recovery', 'recovery_monitor_only'], {'recovery_monitor_only': True}),
    },
    GlobalOperatingMode.THROTTLED: {
        module: GlobalModeEnforcementRule(GlobalOperatingMode.THROTTLED, module, GlobalModeEnforcementEffectType.THROTTLE if module != 'execution_intake' else GlobalModeEnforcementEffectType.BLOCK_NEW_ACTIVITY, 'Throttled mode reduces global runtime intensity and blocks new execution paths.', ['mode:throttled', f'module:{module}'], {'global_throttle_factor': 0.45})
        for module in MODULES
    },
    GlobalOperatingMode.BLOCKED: {
        module: GlobalModeEnforcementRule(GlobalOperatingMode.BLOCKED, module, GlobalModeEnforcementEffectType.MONITOR_ONLY if module in {'heartbeat_runner', 'session_recovery'} else GlobalModeEnforcementEffectType.BLOCK_NEW_ACTIVITY, 'Blocked mode halts new operational activity and keeps only controlled monitoring/recovery.', ['mode:blocked', f'module:{module}'], {'blocked': True})
        for module in MODULES
    },
}


def list_rules_for_mode(mode: str) -> list[GlobalModeEnforcementRule]:
    return [
        _RULES.get(mode, _RULES[GlobalOperatingMode.BALANCED]).get(module)
        for module in MODULES
    ]

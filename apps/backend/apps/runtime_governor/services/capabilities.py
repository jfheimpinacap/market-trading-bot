from __future__ import annotations

from dataclasses import asdict, dataclass

from apps.runtime_governor.models import RuntimeModeProfile
from apps.runtime_governor.services.operating_mode.mode_switch import get_active_global_operating_mode
from apps.safety_guard.services.evaluation import get_safety_status


@dataclass
class RuntimeCapabilities:
    mode: str
    allow_signal_generation: bool
    allow_proposals: bool
    allow_allocation: bool
    allow_real_market_ops: bool
    allow_auto_execution: bool
    allow_continuous_loop: bool
    require_operator_for_all_trades: bool
    allow_pending_approvals: bool
    allow_replay: bool
    allow_experiments: bool
    max_auto_trades_per_cycle: int
    max_auto_trades_per_session: int
    blocked_reasons: list[str]


def profile_to_capabilities(profile: RuntimeModeProfile) -> RuntimeCapabilities:
    return RuntimeCapabilities(
        mode=profile.mode,
        allow_signal_generation=profile.allow_signal_generation,
        allow_proposals=profile.allow_proposals,
        allow_allocation=profile.allow_allocation,
        allow_real_market_ops=profile.allow_real_market_ops,
        allow_auto_execution=profile.allow_auto_execution,
        allow_continuous_loop=profile.allow_continuous_loop,
        require_operator_for_all_trades=profile.require_operator_for_all_trades,
        allow_pending_approvals=profile.allow_pending_approvals,
        allow_replay=profile.allow_replay,
        allow_experiments=profile.allow_experiments,
        max_auto_trades_per_cycle=profile.max_auto_trades_per_cycle,
        max_auto_trades_per_session=profile.max_auto_trades_per_session,
        blocked_reasons=[],
    )


def apply_safety_overrides(caps: RuntimeCapabilities) -> RuntimeCapabilities:
    safety = get_safety_status()
    blocked_reasons: list[str] = []

    if safety['kill_switch_enabled']:
        caps.allow_auto_execution = False
        caps.allow_continuous_loop = False
        blocked_reasons.append('Kill switch is enabled.')

    if safety['hard_stop_active']:
        caps.allow_auto_execution = False
        caps.allow_continuous_loop = False
        blocked_reasons.append('Safety hard stop is active.')

    if safety['status'] in {'COOLDOWN', 'PAUSED'}:
        caps.allow_auto_execution = False
        blocked_reasons.append(f"Safety status {safety['status']} blocks auto execution.")

    caps.blocked_reasons = blocked_reasons
    return caps




def apply_mode_enforcement_overrides(caps: RuntimeCapabilities) -> RuntimeCapabilities:
    from apps.runtime_governor.services.state import get_runtime_state

    state = get_runtime_state()
    enforcement = (state.metadata or {}).get('global_mode_enforcement', {})
    decisions = enforcement.get('enforcement_decisions', []) if isinstance(enforcement, dict) else []
    blocked_modules = {d.get('module_name') for d in decisions if d.get('decision_status') == 'BLOCKED'}

    if 'execution_intake' in blocked_modules:
        caps.allow_auto_execution = False
        caps.blocked_reasons.append('Mode enforcement blocked execution intake.')
    if 'exposure_coordination' in blocked_modules or 'exposure_apply' in blocked_modules:
        caps.allow_allocation = False
        caps.blocked_reasons.append('Mode enforcement blocked new exposure activity.')
    if 'heartbeat_runner' in blocked_modules:
        caps.allow_continuous_loop = False
        caps.blocked_reasons.append('Mode enforcement blocked heartbeat runner cadence.')
    return caps
def get_effective_capabilities(profile: RuntimeModeProfile) -> dict:
    caps = apply_safety_overrides(profile_to_capabilities(profile))
    global_mode = get_active_global_operating_mode()
    if global_mode in {'MONITOR_ONLY', 'RECOVERY_MODE', 'THROTTLED', 'BLOCKED'}:
        caps.allow_auto_execution = False
        caps.allow_continuous_loop = False
        caps.blocked_reasons.append(f'Global operating mode {global_mode} disables autonomous execution.')
    if global_mode in {'THROTTLED', 'BLOCKED'}:
        caps.allow_allocation = False
        caps.blocked_reasons.append(f'Global operating mode {global_mode} reduces allocation privileges.')
    caps = apply_mode_enforcement_overrides(caps)
    return asdict(caps)

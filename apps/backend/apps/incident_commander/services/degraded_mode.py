from __future__ import annotations

from django.utils import timezone

from apps.incident_commander.models import DegradedModeState, DegradedSystemState


def get_current_degraded_mode_state() -> DegradedModeState:
    state = DegradedModeState.objects.order_by('-updated_at', '-id').first()
    if state:
        return state
    return DegradedModeState.objects.create(
        state=DegradedSystemState.NORMAL,
        mission_control_paused=False,
        auto_execution_enabled=True,
        rollout_enabled=True,
        degraded_modules=[],
        disabled_actions=[],
        reasons=[],
        activated_at=timezone.now(),
        metadata={'initialized': True},
    )


def apply_degraded_mode(*, state_code: str, reason: str, degraded_modules: list[str] | None = None, disabled_actions: list[str] | None = None, metadata: dict | None = None, mission_control_paused: bool | None = None, auto_execution_enabled: bool | None = None, rollout_enabled: bool | None = None) -> DegradedModeState:
    state = get_current_degraded_mode_state()
    state.state = state_code
    state.degraded_modules = sorted({*(state.degraded_modules or []), *((degraded_modules or []))})
    state.disabled_actions = sorted({*(state.disabled_actions or []), *((disabled_actions or []))})
    state.reasons = [*(state.reasons or []), reason]
    state.metadata = {**(state.metadata or {}), **(metadata or {})}
    state.activated_at = state.activated_at or timezone.now()

    if mission_control_paused is not None:
        state.mission_control_paused = mission_control_paused
    if auto_execution_enabled is not None:
        state.auto_execution_enabled = auto_execution_enabled
    if rollout_enabled is not None:
        state.rollout_enabled = rollout_enabled

    state.save()
    return state


def reset_degraded_mode(*, reason: str) -> DegradedModeState:
    state = get_current_degraded_mode_state()
    state.state = DegradedSystemState.NORMAL
    state.degraded_modules = []
    state.disabled_actions = []
    state.reasons = [reason]
    state.mission_control_paused = False
    state.auto_execution_enabled = True
    state.rollout_enabled = True
    state.metadata = {**(state.metadata or {}), 'last_reset_reason': reason, 'reset_at': timezone.now().isoformat()}
    state.save()
    return state

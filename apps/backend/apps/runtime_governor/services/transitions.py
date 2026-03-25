from __future__ import annotations

from apps.runtime_governor.models import RuntimeModeState, RuntimeTransitionLog


def log_transition(*, state_before: RuntimeModeState | None, state_after: RuntimeModeState, trigger_source: str, reason: str, metadata: dict | None = None) -> RuntimeTransitionLog:
    return RuntimeTransitionLog.objects.create(
        from_mode=state_before.current_mode if state_before else None,
        to_mode=state_after.current_mode,
        from_status=state_before.status if state_before else None,
        to_status=state_after.status,
        trigger_source=trigger_source,
        reason=reason,
        metadata=metadata or {},
    )

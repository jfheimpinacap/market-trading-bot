from __future__ import annotations

from django.db import transaction

from apps.safety_guard.models import SafetyEvent, SafetyEventSource, SafetyEventType, SafetyPolicyConfig, SafetySeverity, SafetyStatus
from apps.safety_guard.services.kill_switch import get_or_create_config


@transaction.atomic
def trigger_cooldown(*, current_cycle: int, source: str, reason: str, details: dict | None = None) -> SafetyPolicyConfig:
    config = get_or_create_config()
    config.cooldown_until_cycle = current_cycle + max(config.cooldown_cycles, 1)
    config.status = SafetyStatus.COOLDOWN
    config.status_message = reason
    config.paused_by_safety = True
    config.save(update_fields=['cooldown_until_cycle', 'status', 'status_message', 'paused_by_safety', 'updated_at'])

    SafetyEvent.objects.create(
        event_type=SafetyEventType.COOLDOWN_TRIGGERED,
        severity=SafetySeverity.WARNING,
        source=source,
        message=reason,
        details=details or {},
    )
    return config


@transaction.atomic
def clear_cooldown(*, source: str = SafetyEventSource.MANUAL) -> SafetyPolicyConfig:
    config = get_or_create_config()
    config.cooldown_until_cycle = None
    config.paused_by_safety = False
    if not config.hard_stop_active and not config.kill_switch_enabled:
        config.status = SafetyStatus.HEALTHY
        config.status_message = 'Cooldown cleared manually.'
    config.save(update_fields=['cooldown_until_cycle', 'paused_by_safety', 'status', 'status_message', 'updated_at'])

    SafetyEvent.objects.create(
        event_type=SafetyEventType.WARNING,
        severity=SafetySeverity.INFO,
        source=source,
        message='Cooldown manually cleared.',
        details={},
    )
    return config

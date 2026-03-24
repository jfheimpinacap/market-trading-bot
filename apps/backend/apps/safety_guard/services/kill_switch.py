from __future__ import annotations

from django.db import transaction

from apps.continuous_demo.models import LoopRuntimeControl, RuntimeStatus
from apps.safety_guard.models import SafetyEvent, SafetyEventSource, SafetyEventType, SafetyPolicyConfig, SafetySeverity, SafetyStatus


def get_or_create_config() -> SafetyPolicyConfig:
    config = SafetyPolicyConfig.objects.order_by('id').first()
    if config is None:
        config = SafetyPolicyConfig.objects.create(name='default')
    return config



def _get_runtime_control() -> LoopRuntimeControl:
    control = LoopRuntimeControl.objects.order_by('id').first()
    if control is None:
        control = LoopRuntimeControl.objects.create(runtime_status=RuntimeStatus.IDLE, default_settings={})
    return control


@transaction.atomic
def enable_kill_switch(*, source: str = SafetyEventSource.MANUAL, message: str = 'Kill switch enabled manually.') -> SafetyPolicyConfig:
    config = get_or_create_config()
    config.kill_switch_enabled = True
    config.status = SafetyStatus.KILL_SWITCH
    config.status_message = message
    config.save(update_fields=['kill_switch_enabled', 'status', 'status_message', 'updated_at'])

    control = _get_runtime_control()
    control.kill_switch = True
    control.stop_requested = True
    control.pause_requested = False
    control.runtime_status = RuntimeStatus.STOPPED
    control.save(update_fields=['kill_switch', 'stop_requested', 'pause_requested', 'runtime_status', 'updated_at'])

    SafetyEvent.objects.create(
        event_type=SafetyEventType.KILL_SWITCH_TRIGGERED,
        severity=SafetySeverity.CRITICAL,
        source=source,
        message=message,
        details={'kill_switch_enabled': True},
    )
    return config


@transaction.atomic
def disable_kill_switch(*, source: str = SafetyEventSource.MANUAL, message: str = 'Kill switch disabled manually.') -> SafetyPolicyConfig:
    config = get_or_create_config()
    config.kill_switch_enabled = False
    if config.hard_stop_active:
        config.status = SafetyStatus.HARD_STOP
        config.status_message = 'Kill switch disabled, but hard stop is still active.'
    elif config.cooldown_until_cycle:
        config.status = SafetyStatus.COOLDOWN
        config.status_message = 'Kill switch disabled; cooldown remains active.'
    else:
        config.status = SafetyStatus.HEALTHY
        config.status_message = 'Safety state reset to healthy.'

    config.save(update_fields=['kill_switch_enabled', 'status', 'status_message', 'updated_at'])

    control = _get_runtime_control()
    control.kill_switch = False
    control.stop_requested = False
    if control.runtime_status == RuntimeStatus.STOPPED:
        control.runtime_status = RuntimeStatus.IDLE
    control.save(update_fields=['kill_switch', 'stop_requested', 'runtime_status', 'updated_at'])

    SafetyEvent.objects.create(
        event_type=SafetyEventType.WARNING,
        severity=SafetySeverity.INFO,
        source=source,
        message=message,
        details={'kill_switch_enabled': False},
    )
    return config

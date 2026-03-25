from __future__ import annotations

from copy import deepcopy

from django.db import transaction
from django.utils import timezone

from apps.continuous_demo.models import LoopRuntimeControl, RuntimeStatus

DEFAULT_LOOP_SETTINGS = {
    'enabled': True,
    'cycle_interval_seconds': 30,
    'max_cycles_per_session': None,
    'max_auto_trades_per_cycle': 2,
    'max_auto_trades_total_per_session': 20,
    'stop_on_error': False,
    'market_scope': 'mixed',
    'review_after_trade': True,
    'revalue_after_trade': True,
    'market_limit_per_cycle': 8,
    'learning_rebuild_enabled': False,
    'learning_rebuild_every_n_cycles': 10,
    'learning_rebuild_after_reviews': False,
    'learning_max_adjustment_magnitude': '0.2000',
    'real_data_refresh_enabled': False,
    'real_data_refresh_every_n_cycles': 5,
    'real_data_refresh_active_only': True,
    'real_data_refresh_limit': 50,
    'use_real_market_scope': False,
}


def normalize_settings(overrides: dict | None = None) -> dict:
    settings = deepcopy(DEFAULT_LOOP_SETTINGS)
    if overrides:
        settings.update({key: value for key, value in overrides.items() if value is not None})
    return settings


@transaction.atomic
def get_runtime_control() -> LoopRuntimeControl:
    control = LoopRuntimeControl.objects.select_for_update().first()
    if control is None:
        control = LoopRuntimeControl.objects.create(default_settings=deepcopy(DEFAULT_LOOP_SETTINGS), runtime_status=RuntimeStatus.IDLE)
    elif not control.default_settings:
        control.default_settings = deepcopy(DEFAULT_LOOP_SETTINGS)
        control.save(update_fields=['default_settings', 'updated_at'])
    return control


def heartbeat(*, error: str = '') -> None:
    with transaction.atomic():
        control = get_runtime_control()
        control.last_heartbeat_at = timezone.now()
        if error:
            control.last_error = error
        control.save(update_fields=['last_heartbeat_at', 'last_error', 'updated_at'])

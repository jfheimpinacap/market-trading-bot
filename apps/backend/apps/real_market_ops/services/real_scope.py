from __future__ import annotations

from copy import deepcopy

from apps.real_market_ops.models import RealScopeConfig

DEFAULT_REAL_SCOPE_CONFIG: dict = {
    'enabled': False,
    'provider_scope': 'all',
    'market_scope': 'active_only',
    'max_real_markets_per_cycle': 8,
    'max_real_auto_trades_per_cycle': 1,
    'max_real_exposure_total': '2500.00',
    'max_real_exposure_per_market': '500.00',
    'require_fresh_sync': True,
    'stale_data_blocks_execution': True,
    'degraded_provider_blocks_execution': True,
    'min_liquidity_threshold': '0',
    'min_volume_threshold': '0',
    'allowed_categories': [],
    'exclude_categories': [],
}


def get_real_scope_config() -> RealScopeConfig:
    config = RealScopeConfig.objects.first()
    if config is None:
        config = RealScopeConfig.objects.create(**deepcopy(DEFAULT_REAL_SCOPE_CONFIG))
    return config


def get_real_scope_payload() -> dict:
    config = get_real_scope_config()
    return {
        'id': config.id,
        'enabled': config.enabled,
        'provider_scope': config.provider_scope,
        'market_scope': config.market_scope,
        'max_real_markets_per_cycle': config.max_real_markets_per_cycle,
        'max_real_auto_trades_per_cycle': config.max_real_auto_trades_per_cycle,
        'max_real_exposure_total': str(config.max_real_exposure_total),
        'max_real_exposure_per_market': str(config.max_real_exposure_per_market),
        'require_fresh_sync': config.require_fresh_sync,
        'stale_data_blocks_execution': config.stale_data_blocks_execution,
        'degraded_provider_blocks_execution': config.degraded_provider_blocks_execution,
        'min_liquidity_threshold': str(config.min_liquidity_threshold),
        'min_volume_threshold': str(config.min_volume_threshold),
        'allowed_categories': config.allowed_categories,
        'exclude_categories': config.exclude_categories,
    }

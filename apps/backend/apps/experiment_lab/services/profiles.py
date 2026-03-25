from apps.experiment_lab.models import StrategyProfile

BASE_PROFILES = [
    {
        'name': 'Conservative',
        'slug': 'conservative',
        'description': 'Lower execution intensity, stricter safety posture, demo-only scope.',
        'profile_type': 'conservative',
        'market_scope': 'demo_only',
        'config': {
            'allocation': {'max_trade_notional': 150, 'max_daily_notional': 500, 'position_cap_pct': 0.05},
            'safety': {'max_blocks_before_pause': 3, 'cooldown_minutes': 20, 'hard_stop_enabled': True},
            'policy': {'approval_threshold': 'high', 'require_manual_above_size': True},
            'learning': {'enabled': True, 'conservative_bias': 0.2},
            'replay': {'market_limit': 6, 'auto_execute_allowed': False, 'treat_approval_required_as_skip': True},
        },
    },
    {
        'name': 'Balanced',
        'slug': 'balanced',
        'description': 'General-purpose baseline profile for replay and live-paper evaluation.',
        'profile_type': 'balanced',
        'market_scope': 'mixed',
        'config': {
            'allocation': {'max_trade_notional': 250, 'max_daily_notional': 1200, 'position_cap_pct': 0.1},
            'safety': {'max_blocks_before_pause': 5, 'cooldown_minutes': 10, 'hard_stop_enabled': True},
            'policy': {'approval_threshold': 'medium', 'require_manual_above_size': True},
            'learning': {'enabled': True, 'conservative_bias': 0.1},
            'replay': {'market_limit': 8, 'auto_execute_allowed': True, 'treat_approval_required_as_skip': True},
        },
    },
    {
        'name': 'Aggressive-light',
        'slug': 'aggressive-light',
        'description': 'Higher activity profile while still paper/demo-only and safety-governed.',
        'profile_type': 'aggressive',
        'market_scope': 'mixed',
        'config': {
            'allocation': {'max_trade_notional': 350, 'max_daily_notional': 2000, 'position_cap_pct': 0.15},
            'safety': {'max_blocks_before_pause': 7, 'cooldown_minutes': 5, 'hard_stop_enabled': True},
            'policy': {'approval_threshold': 'medium_low', 'require_manual_above_size': False},
            'learning': {'enabled': True, 'conservative_bias': 0.0},
            'replay': {'market_limit': 12, 'auto_execute_allowed': True, 'treat_approval_required_as_skip': False},
        },
    },
    {
        'name': 'Real-only conservative',
        'slug': 'real-only-conservative',
        'description': 'Conservative profile for read-only real market scope with paper execution only.',
        'profile_type': 'conservative',
        'market_scope': 'real_only',
        'config': {
            'allocation': {'max_trade_notional': 120, 'max_daily_notional': 400, 'position_cap_pct': 0.04},
            'safety': {'max_blocks_before_pause': 3, 'cooldown_minutes': 30, 'hard_stop_enabled': True},
            'policy': {'approval_threshold': 'high', 'require_manual_above_size': True},
            'learning': {'enabled': True, 'conservative_bias': 0.25},
            'replay': {'market_limit': 5, 'auto_execute_allowed': False, 'treat_approval_required_as_skip': True},
        },
    },
    {
        'name': 'Mixed conservative',
        'slug': 'mixed-conservative',
        'description': 'Cross-source conservative profile for replay-vs-live consistency checks.',
        'profile_type': 'conservative',
        'market_scope': 'mixed',
        'config': {
            'allocation': {'max_trade_notional': 180, 'max_daily_notional': 700, 'position_cap_pct': 0.06},
            'safety': {'max_blocks_before_pause': 4, 'cooldown_minutes': 15, 'hard_stop_enabled': True},
            'policy': {'approval_threshold': 'high', 'require_manual_above_size': True},
            'learning': {'enabled': True, 'conservative_bias': 0.15},
            'replay': {'market_limit': 7, 'auto_execute_allowed': False, 'treat_approval_required_as_skip': True},
        },
    },
]


def seed_strategy_profiles() -> dict:
    created = 0
    updated = 0
    for payload in BASE_PROFILES:
        _, was_created = StrategyProfile.objects.update_or_create(
            slug=payload['slug'],
            defaults=payload,
        )
        if was_created:
            created += 1
        else:
            updated += 1
    return {'created': created, 'updated': updated, 'total': StrategyProfile.objects.count()}

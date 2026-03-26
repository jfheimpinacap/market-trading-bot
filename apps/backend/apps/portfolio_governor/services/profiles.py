DEFAULT_PROFILE = {
    'slug': 'balanced_portfolio_governor',
    'label': 'Balanced portfolio governor',
    'max_open_positions': 8,
    'max_market_concentration_ratio': 0.45,
    'max_provider_concentration_ratio': 0.55,
    'drawdown_caution_pct': 0.06,
    'drawdown_throttle_pct': 0.10,
    'drawdown_block_pct': 0.14,
    'cash_reserve_caution_ratio': 0.20,
    'cash_reserve_throttle_ratio': 0.12,
    'cash_reserve_block_ratio': 0.08,
    'close_reduce_events_caution': 3,
    'close_reduce_events_throttle': 5,
    'queue_pressure_caution': 4,
    'queue_pressure_throttle': 8,
    'default_max_new_positions': 3,
}

CONSERVATIVE_PROFILE = {
    **DEFAULT_PROFILE,
    'slug': 'conservative_portfolio_governor',
    'label': 'Conservative portfolio governor',
    'max_open_positions': 6,
    'max_market_concentration_ratio': 0.35,
    'max_provider_concentration_ratio': 0.45,
    'drawdown_caution_pct': 0.04,
    'drawdown_throttle_pct': 0.07,
    'drawdown_block_pct': 0.1,
    'default_max_new_positions': 2,
}

PROFILE_MAP = {p['slug']: p for p in (DEFAULT_PROFILE, CONSERVATIVE_PROFILE)}


def get_profile(slug: str | None) -> dict:
    if slug and slug in PROFILE_MAP:
        return PROFILE_MAP[slug]
    return DEFAULT_PROFILE


def list_profiles() -> list[dict]:
    return [PROFILE_MAP[key] for key in sorted(PROFILE_MAP.keys())]

DEFAULT_PROFILE = {
    'slug': 'balanced_mission_control',
    'label': 'Balanced mission control',
    'cycle_interval_seconds': 45,
    'run_research_every_n_cycles': 2,
    'run_universe_scan_every_n_cycles': 2,
    'run_watch_every_cycle': True,
    'run_position_lifecycle_every_cycle': True,
    'run_digest_every_n_cycles': 3,
    'run_postmortem_every_n_cycles': 5,
    'run_learning_rebuild_every_n_cycles': 8,
    'max_cycles_per_session': None,
    'research_source_ids': None,
    'universe_filter_profile': 'balanced_scan',
    'opportunity_profile_slug': 'balanced_supervisor',
}

CONSERVATIVE_PROFILE = {
    **DEFAULT_PROFILE,
    'slug': 'conservative_mission_control',
    'label': 'Conservative mission control',
    'cycle_interval_seconds': 60,
    'run_research_every_n_cycles': 3,
    'run_digest_every_n_cycles': 4,
    'opportunity_profile_slug': 'conservative_supervisor',
}

PROFILE_MAP = {p['slug']: p for p in (DEFAULT_PROFILE, CONSERVATIVE_PROFILE)}


def list_profiles() -> list[dict]:
    return [PROFILE_MAP[key] for key in sorted(PROFILE_MAP.keys())]


def get_profile(slug: str | None) -> dict:
    if slug and slug in PROFILE_MAP:
        return PROFILE_MAP[slug]
    return DEFAULT_PROFILE

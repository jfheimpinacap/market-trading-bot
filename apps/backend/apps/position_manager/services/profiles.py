DEFAULT_PROFILE = {
    'slug': 'balanced_lifecycle',
    'label': 'Balanced lifecycle governance',
    'description': 'Default hold/reduce/close/review policy for paper position lifecycle management.',
}

PROFILE_MAP = {
    DEFAULT_PROFILE['slug']: DEFAULT_PROFILE,
}


def list_profiles() -> list[dict]:
    return [PROFILE_MAP[key] for key in sorted(PROFILE_MAP.keys())]

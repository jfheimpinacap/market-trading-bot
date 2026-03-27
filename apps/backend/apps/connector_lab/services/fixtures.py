from apps.connector_lab.models import ConnectorFixtureProfile

FIXTURE_DEFINITIONS = {
    'generic_binary_market_fixture': {
        'display_name': 'Generic binary market fixture',
        'description': 'Baseline fixture for standard binary market buy/sell payload and response normalization checks.',
        'metadata': {'force_manual_confirmation': False, 'inject_reconciliation_drift': False, 'unsupported_capability': None},
    },
    'partial_fill_fixture': {
        'display_name': 'Partial fill fixture',
        'description': 'Uses larger quantity to exercise HOLD/PARTIAL-like normalization behavior in sandbox.',
        'metadata': {'quantity': '120.0000', 'inject_reconciliation_drift': False, 'unsupported_capability': None},
    },
    'rejection_fixture': {
        'display_name': 'Rejection fixture',
        'description': 'Injects invalid payload conditions to verify rejection normalization.',
        'metadata': {'force_missing_market': True, 'inject_reconciliation_drift': False, 'unsupported_capability': None},
    },
    'reconciliation_drift_fixture': {
        'display_name': 'Reconciliation drift fixture',
        'description': 'Injects account drift metadata so reconciliation mismatch paths are auditable.',
        'metadata': {'inject_reconciliation_drift': True, 'unsupported_capability': None},
    },
    'unsupported_capability_fixture': {
        'display_name': 'Unsupported capability fixture',
        'description': 'Temporarily disables one capability to validate unsupported mapping behavior.',
        'metadata': {'inject_reconciliation_drift': False, 'unsupported_capability': 'supports_close_order'},
    },
}


def ensure_fixture_profiles() -> list[ConnectorFixtureProfile]:
    profiles: list[ConnectorFixtureProfile] = []
    for slug, cfg in FIXTURE_DEFINITIONS.items():
        profile, _ = ConnectorFixtureProfile.objects.get_or_create(
            slug=slug,
            defaults={
                'display_name': cfg['display_name'],
                'description': cfg['description'],
                'metadata': cfg['metadata'],
            },
        )
        profiles.append(profile)
    return profiles


def get_fixture_profile(slug: str | None) -> ConnectorFixtureProfile:
    ensure_fixture_profiles()
    if slug:
        return ConnectorFixtureProfile.objects.get(slug=slug)
    return ConnectorFixtureProfile.objects.get(slug='generic_binary_market_fixture')

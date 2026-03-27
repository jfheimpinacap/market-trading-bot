from apps.execution_venue.models import VenueCapabilityProfile

DEFAULT_ADAPTER_NAME = 'null_sandbox'
DEFAULT_VENUE_NAME = 'sandbox_venue'


def get_or_create_default_capabilities() -> VenueCapabilityProfile:
    capability, _ = VenueCapabilityProfile.objects.get_or_create(
        adapter_name=DEFAULT_ADAPTER_NAME,
        defaults={
            'venue_name': DEFAULT_VENUE_NAME,
            'supports_market_like': True,
            'supports_limit_like': True,
            'supports_reduce_only': True,
            'supports_close_order': True,
            'supports_partial_updates': False,
            'requires_symbol_mapping': True,
            'requires_manual_confirmation': False,
            'paper_only_supported': True,
            'live_supported': False,
            'metadata': {'sandbox_only': True, 'real_execution_enabled': False},
        },
    )
    return capability


def serialize_capability(capability: VenueCapabilityProfile) -> dict:
    return {
        'id': capability.id,
        'adapter_name': capability.adapter_name,
        'venue_name': capability.venue_name,
        'supports_market_like': capability.supports_market_like,
        'supports_limit_like': capability.supports_limit_like,
        'supports_reduce_only': capability.supports_reduce_only,
        'supports_close_order': capability.supports_close_order,
        'supports_partial_updates': capability.supports_partial_updates,
        'requires_symbol_mapping': capability.requires_symbol_mapping,
        'requires_manual_confirmation': capability.requires_manual_confirmation,
        'paper_only_supported': capability.paper_only_supported,
        'live_supported': capability.live_supported,
        'metadata': capability.metadata,
        'updated_at': capability.updated_at,
    }

from __future__ import annotations

from apps.profile_manager.models import ManagedProfileBinding


DEFAULT_BINDINGS = [
    {'module_key': 'research_agent', 'operating_mode': 'conservative', 'profile_slug': 'conservative_scan', 'profile_label': 'Conservative scan'},
    {'module_key': 'research_agent', 'operating_mode': 'balanced', 'profile_slug': 'balanced_scan', 'profile_label': 'Balanced scan'},
    {'module_key': 'research_agent', 'operating_mode': 'aggressive_light', 'profile_slug': 'broad_scan', 'profile_label': 'Broad scan'},
    {'module_key': 'signals', 'operating_mode': 'conservative', 'profile_slug': 'conservative_signal', 'profile_label': 'Conservative signal'},
    {'module_key': 'signals', 'operating_mode': 'balanced', 'profile_slug': 'balanced_signal', 'profile_label': 'Balanced signal'},
    {'module_key': 'signals', 'operating_mode': 'aggressive_light', 'profile_slug': 'aggressive_light_signal', 'profile_label': 'Aggressive light signal'},
    {'module_key': 'opportunity_supervisor', 'operating_mode': 'conservative', 'profile_slug': 'conservative_supervisor', 'profile_label': 'Conservative supervisor'},
    {'module_key': 'opportunity_supervisor', 'operating_mode': 'balanced', 'profile_slug': 'balanced_supervisor', 'profile_label': 'Balanced supervisor'},
    {'module_key': 'opportunity_supervisor', 'operating_mode': 'aggressive_light', 'profile_slug': 'aggressive_supervisor', 'profile_label': 'Aggressive supervisor'},
    {'module_key': 'mission_control', 'operating_mode': 'conservative', 'profile_slug': 'conservative_mission_control', 'profile_label': 'Conservative mission control'},
    {'module_key': 'mission_control', 'operating_mode': 'balanced', 'profile_slug': 'balanced_mission_control', 'profile_label': 'Balanced mission control'},
    {'module_key': 'mission_control', 'operating_mode': 'aggressive_light', 'profile_slug': 'balanced_mission_control', 'profile_label': 'Balanced mission control'},
    {'module_key': 'portfolio_governor', 'operating_mode': 'conservative', 'profile_slug': 'conservative_portfolio_governor', 'profile_label': 'Conservative portfolio governor'},
    {'module_key': 'portfolio_governor', 'operating_mode': 'balanced', 'profile_slug': 'balanced_portfolio_governor', 'profile_label': 'Balanced portfolio governor'},
    {'module_key': 'portfolio_governor', 'operating_mode': 'aggressive_light', 'profile_slug': 'balanced_portfolio_governor', 'profile_label': 'Balanced portfolio governor'},
]


def ensure_default_bindings() -> None:
    for item in DEFAULT_BINDINGS:
        ManagedProfileBinding.objects.update_or_create(
            module_key=item['module_key'],
            operating_mode=item['operating_mode'],
            defaults={
                'profile_slug': item['profile_slug'],
                'profile_label': item['profile_label'],
                'is_active': True,
            },
        )


def resolve_profile(module_key: str, operating_mode: str) -> str:
    ensure_default_bindings()
    binding = ManagedProfileBinding.objects.filter(module_key=module_key, operating_mode=operating_mode, is_active=True).first()
    if binding:
        return binding.profile_slug
    fallback = ManagedProfileBinding.objects.filter(module_key=module_key, operating_mode='balanced', is_active=True).first()
    if fallback:
        return fallback.profile_slug
    return ''


def list_bindings() -> list[ManagedProfileBinding]:
    ensure_default_bindings()
    return list(ManagedProfileBinding.objects.filter(is_active=True).order_by('module_key', 'operating_mode'))

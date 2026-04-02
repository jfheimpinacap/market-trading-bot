from __future__ import annotations

from apps.mission_control.models import AutonomousScheduleProfile, AutonomousRuntimeSession


DEFAULT_PROFILES = [
    {
        'slug': 'balanced_local',
        'display_name': 'Balanced local',
        'base_interval_seconds': 60,
        'reduced_interval_seconds': 30,
        'monitor_only_interval_seconds': 180,
        'cooldown_extension_seconds': 120,
        'max_no_action_ticks_before_pause': 5,
        'max_quiet_ticks_before_wait_long': 3,
        'max_consecutive_blocked_ticks_before_stop': 4,
        'enable_auto_pause_for_quiet_markets': True,
        'enable_auto_stop_for_persistent_blocks': True,
        'metadata': {'tier': 'default'},
    },
    {
        'slug': 'conservative_quiet',
        'display_name': 'Conservative quiet',
        'base_interval_seconds': 90,
        'reduced_interval_seconds': 45,
        'monitor_only_interval_seconds': 240,
        'cooldown_extension_seconds': 180,
        'max_no_action_ticks_before_pause': 4,
        'max_quiet_ticks_before_wait_long': 2,
        'max_consecutive_blocked_ticks_before_stop': 3,
        'enable_auto_pause_for_quiet_markets': True,
        'enable_auto_stop_for_persistent_blocks': True,
        'metadata': {'tier': 'quiet'},
    },
    {
        'slug': 'monitor_heavy',
        'display_name': 'Monitor heavy',
        'base_interval_seconds': 120,
        'reduced_interval_seconds': 60,
        'monitor_only_interval_seconds': 300,
        'cooldown_extension_seconds': 240,
        'max_no_action_ticks_before_pause': 6,
        'max_quiet_ticks_before_wait_long': 2,
        'max_consecutive_blocked_ticks_before_stop': 5,
        'enable_auto_pause_for_quiet_markets': True,
        'enable_auto_stop_for_persistent_blocks': False,
        'metadata': {'tier': 'monitor'},
    },
]


def ensure_default_schedule_profiles() -> list[AutonomousScheduleProfile]:
    profiles: list[AutonomousScheduleProfile] = []
    for payload in DEFAULT_PROFILES:
        profile, _ = AutonomousScheduleProfile.objects.update_or_create(slug=payload['slug'], defaults=payload)
        profiles.append(profile)
    return profiles


def get_default_profile() -> AutonomousScheduleProfile:
    ensure_default_schedule_profiles()
    preferred = AutonomousScheduleProfile.objects.filter(slug='balanced_local', is_active=True).first()
    if preferred:
        return preferred
    fallback = AutonomousScheduleProfile.objects.filter(is_active=True).order_by('id').first()
    if fallback:
        return fallback
    return ensure_default_schedule_profiles()[0]


def resolve_profile_for_session(*, session: AutonomousRuntimeSession) -> AutonomousScheduleProfile:
    if session.linked_schedule_profile_id and session.linked_schedule_profile and session.linked_schedule_profile.is_active:
        return session.linked_schedule_profile

    profile = AutonomousScheduleProfile.objects.filter(slug=session.profile_slug, is_active=True).first() if session.profile_slug else None
    if not profile:
        profile = get_default_profile()
    if session.linked_schedule_profile_id != profile.id:
        session.linked_schedule_profile = profile
        session.save(update_fields=['linked_schedule_profile', 'updated_at'])
    return profile


def apply_schedule_profile(*, session: AutonomousRuntimeSession, profile: AutonomousScheduleProfile) -> AutonomousRuntimeSession:
    session.linked_schedule_profile = profile
    session.profile_slug = profile.slug
    session.save(update_fields=['linked_schedule_profile', 'profile_slug', 'updated_at'])
    return session

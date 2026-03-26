from dataclasses import dataclass


@dataclass(frozen=True)
class OpportunitySupervisorProfile:
    slug: str
    label: str
    fusion_profile_slug: str
    queue_high_risk: bool = True
    min_gate_priority: int = 70


DEFAULT_PROFILE = OpportunitySupervisorProfile(
    slug='balanced_supervisor',
    label='Balanced supervisor',
    fusion_profile_slug='balanced_signal',
    queue_high_risk=True,
    min_gate_priority=70,
)

PROFILES = {
    DEFAULT_PROFILE.slug: DEFAULT_PROFILE,
    'conservative_supervisor': OpportunitySupervisorProfile(
        slug='conservative_supervisor',
        label='Conservative supervisor',
        fusion_profile_slug='conservative_signal',
        queue_high_risk=True,
        min_gate_priority=80,
    ),
    'aggressive_supervisor': OpportunitySupervisorProfile(
        slug='aggressive_supervisor',
        label='Aggressive supervisor',
        fusion_profile_slug='aggressive_light_signal',
        queue_high_risk=False,
        min_gate_priority=65,
    ),
}


def get_profile(slug: str | None) -> OpportunitySupervisorProfile:
    if not slug:
        return DEFAULT_PROFILE
    return PROFILES.get(slug, DEFAULT_PROFILE)


def list_profiles() -> list[dict]:
    return [
        {
            'slug': profile.slug,
            'label': profile.label,
            'fusion_profile_slug': profile.fusion_profile_slug,
            'queue_high_risk': profile.queue_high_risk,
            'min_gate_priority': profile.min_gate_priority,
        }
        for profile in PROFILES.values()
    ]

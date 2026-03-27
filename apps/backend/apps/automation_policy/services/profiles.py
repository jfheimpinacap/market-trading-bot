from django.db import transaction

from apps.automation_policy.models import AutomationPolicyProfile


DEFAULT_PROFILES = [
    {
        'slug': 'conservative_manual_first',
        'name': 'Conservative manual-first',
        'description': 'Manual-first baseline with strict approval gates and no autonomous remediation.',
        'recommendation_mode': True,
        'allow_runbook_auto_advance': False,
        'is_default': True,
        'metadata': {'paper_only': True, 'execution_mode': 'sandbox_only'},
    },
    {
        'slug': 'balanced_assist',
        'name': 'Balanced assist',
        'description': 'Allows low-impact paper/sandbox automation while preserving approval for sensitive actions.',
        'recommendation_mode': False,
        'allow_runbook_auto_advance': True,
        'metadata': {'paper_only': True, 'execution_mode': 'sandbox_only'},
    },
    {
        'slug': 'supervised_autopilot',
        'name': 'Supervised autopilot',
        'description': 'Most permissive supervised tier in paper-only mode with explicit hard blocks for live domains.',
        'recommendation_mode': False,
        'allow_runbook_auto_advance': True,
        'metadata': {'paper_only': True, 'execution_mode': 'sandbox_only'},
    },
]


@transaction.atomic
def ensure_default_profiles() -> list[AutomationPolicyProfile]:
    profiles = []
    for profile in DEFAULT_PROFILES:
        defaults = {key: value for key, value in profile.items() if key not in {'slug', 'is_default'}}
        obj, _ = AutomationPolicyProfile.objects.update_or_create(slug=profile['slug'], defaults=defaults)
        profiles.append(obj)

    active = AutomationPolicyProfile.objects.filter(is_active=True).first()
    if not active:
        default_profile = AutomationPolicyProfile.objects.get(slug='conservative_manual_first')
        default_profile.is_active = True
        default_profile.is_default = True
        default_profile.save(update_fields=['is_active', 'is_default', 'updated_at'])

    return list(AutomationPolicyProfile.objects.order_by('name', 'id'))


def list_profiles() -> list[AutomationPolicyProfile]:
    ensure_default_profiles()
    return list(AutomationPolicyProfile.objects.order_by('name', 'id'))


def get_active_profile() -> AutomationPolicyProfile:
    ensure_default_profiles()
    profile = AutomationPolicyProfile.objects.filter(is_active=True).first()
    if profile:
        return profile
    fallback = AutomationPolicyProfile.objects.get(slug='conservative_manual_first')
    fallback.is_active = True
    fallback.save(update_fields=['is_active', 'updated_at'])
    return fallback


@transaction.atomic
def apply_profile(*, profile_slug: str) -> AutomationPolicyProfile:
    ensure_default_profiles()
    profile = AutomationPolicyProfile.objects.get(slug=profile_slug)
    AutomationPolicyProfile.objects.exclude(pk=profile.pk).filter(is_active=True).update(is_active=False)
    profile.is_active = True
    profile.save(update_fields=['is_active', 'updated_at'])
    return profile

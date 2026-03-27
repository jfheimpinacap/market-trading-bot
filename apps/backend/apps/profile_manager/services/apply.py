from __future__ import annotations

from django.utils import timezone

from apps.mission_control.models import MissionControlState
from apps.profile_manager.models import ProfileDecision


def apply_profile_decision(decision: ProfileDecision, *, applied_by: str = 'profile_manager') -> ProfileDecision:
    state = MissionControlState.objects.order_by('id').first()
    if state is not None:
        state.profile_slug = decision.target_mission_control_profile
        state.settings_snapshot = {
            **(state.settings_snapshot or {}),
            'meta_governance': {
                'profile_decision_id': decision.id,
                'applied_by': applied_by,
                'applied_at': timezone.now().isoformat(),
                'target_opportunity_profile': decision.target_opportunity_supervisor_profile,
                'target_portfolio_profile': decision.target_portfolio_governor_profile,
                'target_research_profile': decision.target_research_profile,
                'target_signal_profile': decision.target_signal_profile,
            },
        }
        state.save(update_fields=['profile_slug', 'settings_snapshot', 'updated_at'])

    decision.is_applied = True
    decision.applied_at = timezone.now()
    decision.save(update_fields=['is_applied', 'applied_at', 'updated_at'])
    return decision


def get_effective_profile_targets() -> dict:
    decision = ProfileDecision.objects.select_related('run').order_by('-created_at', '-id').first()
    if decision is None:
        return {}
    return {
        'target_research_profile': decision.target_research_profile,
        'target_signal_profile': decision.target_signal_profile,
        'target_opportunity_supervisor_profile': decision.target_opportunity_supervisor_profile,
        'target_mission_control_profile': decision.target_mission_control_profile,
        'target_portfolio_governor_profile': decision.target_portfolio_governor_profile,
        'decision_mode': decision.decision_mode,
        'is_applied': decision.is_applied,
    }

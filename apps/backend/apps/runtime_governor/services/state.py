from __future__ import annotations

from django.utils import timezone

from apps.runtime_governor.models import RuntimeMode, RuntimeModeProfile, RuntimeModeState, RuntimeSetBy


MODE_PROFILE_DEFAULTS = {
    RuntimeMode.OBSERVE_ONLY: {
        'label': 'Observe only',
        'description': 'Signals/proposals/evaluation allowed; no automated paper execution.',
        'allow_signal_generation': True,
        'allow_proposals': True,
        'allow_allocation': True,
        'allow_real_market_ops': False,
        'allow_auto_execution': False,
        'allow_continuous_loop': False,
        'require_operator_for_all_trades': True,
        'allow_pending_approvals': True,
        'allow_replay': True,
        'allow_experiments': True,
        'max_auto_trades_per_cycle': 0,
        'max_auto_trades_per_session': 0,
    },
    RuntimeMode.PAPER_ASSIST: {
        'label': 'Paper assist',
        'description': 'Paper proposals allowed, every trade requires operator queue.',
        'allow_signal_generation': True,
        'allow_proposals': True,
        'allow_allocation': True,
        'allow_real_market_ops': True,
        'allow_auto_execution': False,
        'allow_continuous_loop': True,
        'require_operator_for_all_trades': True,
        'allow_pending_approvals': True,
        'allow_replay': True,
        'allow_experiments': True,
        'max_auto_trades_per_cycle': 0,
        'max_auto_trades_per_session': 0,
    },
    RuntimeMode.PAPER_SEMI_AUTO: {
        'label': 'Paper semi-auto',
        'description': 'Auto execution for auto-approved proposals; approval-required stays in queue.',
        'allow_signal_generation': True,
        'allow_proposals': True,
        'allow_allocation': True,
        'allow_real_market_ops': True,
        'allow_auto_execution': True,
        'allow_continuous_loop': True,
        'require_operator_for_all_trades': False,
        'allow_pending_approvals': True,
        'allow_replay': True,
        'allow_experiments': True,
        'max_auto_trades_per_cycle': 2,
        'max_auto_trades_per_session': 12,
    },
    RuntimeMode.PAPER_AUTO: {
        'label': 'Paper auto',
        'description': 'Maximum paper/demo autonomy, still constrained by safety and policy.',
        'allow_signal_generation': True,
        'allow_proposals': True,
        'allow_allocation': True,
        'allow_real_market_ops': True,
        'allow_auto_execution': True,
        'allow_continuous_loop': True,
        'require_operator_for_all_trades': False,
        'allow_pending_approvals': True,
        'allow_replay': True,
        'allow_experiments': True,
        'max_auto_trades_per_cycle': 4,
        'max_auto_trades_per_session': 24,
    },
}


def seed_mode_profiles() -> dict:
    created = 0
    updated = 0
    for mode, defaults in MODE_PROFILE_DEFAULTS.items():
        profile, was_created = RuntimeModeProfile.objects.update_or_create(mode=mode, defaults=defaults)
        if was_created:
            created += 1
        else:
            updated += 1
    return {'created': created, 'updated': updated, 'total': RuntimeModeProfile.objects.count()}


def get_mode_profile(mode: str) -> RuntimeModeProfile:
    seed_mode_profiles()
    return RuntimeModeProfile.objects.get(mode=mode)


def list_mode_profiles():
    seed_mode_profiles()
    return RuntimeModeProfile.objects.order_by('mode')


def get_runtime_state() -> RuntimeModeState:
    seed_mode_profiles()
    state = RuntimeModeState.objects.order_by('id').first()
    if state is None:
        state = RuntimeModeState.objects.create(
            current_mode=RuntimeMode.OBSERVE_ONLY,
            status='ACTIVE',
            set_by=RuntimeSetBy.MANUAL,
            rationale='Default bootstrap mode for local paper/demo runtime.',
            effective_at=timezone.now(),
            metadata={'bootstrap': True},
        )
    return state

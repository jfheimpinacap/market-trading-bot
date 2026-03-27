from __future__ import annotations

from django.utils import timezone

from apps.profile_manager.models import ProfileDecision, ProfileDecisionMode, ProfileGovernanceRun, ProfileGovernanceRunStatus
from apps.profile_manager.services.apply import apply_profile_decision
from apps.profile_manager.services.decision import build_profile_decision
from apps.profile_manager.services.regime import classify_regime
from apps.profile_manager.services.state import build_profile_state_snapshot


def run_profile_governance(*, decision_mode: str | None = None, triggered_by: str = 'manual_api') -> ProfileGovernanceRun:
    run = ProfileGovernanceRun.objects.create(
        status=ProfileGovernanceRunStatus.RUNNING,
        triggered_by=triggered_by,
        started_at=timezone.now(),
        details={'paper_demo_only': True, 'real_execution_enabled': False},
    )

    state = build_profile_state_snapshot()
    regime, reason_codes, constraints = classify_regime(state)
    decision_payload = build_profile_decision(
        regime=regime,
        state=state,
        requested_mode=decision_mode,
        reason_codes=reason_codes,
        constraints=constraints,
    )
    decision = ProfileDecision.objects.create(run=run, **decision_payload)

    should_apply = decision.decision_mode in {ProfileDecisionMode.APPLY_SAFE, ProfileDecisionMode.APPLY_FORCED}
    if should_apply:
        apply_profile_decision(decision, applied_by=triggered_by)

    run.status = ProfileGovernanceRunStatus.COMPLETED
    run.regime = regime
    run.runtime_mode = state.get('runtime_mode', '')
    run.readiness_status = state.get('readiness_status', '')
    run.safety_status = state.get('safety_status', '')
    run.finished_at = timezone.now()
    run.summary = f"Profile governance {regime}: mode={decision.decision_mode}, applied={decision.is_applied}."
    run.details = {
        **run.details,
        'state_snapshot': state,
        'reason_codes': reason_codes,
        'blocking_constraints': constraints,
        'handoffs': [
            'portfolio_governor -> profile_manager',
            'profile_manager -> mission_control',
            'profile_manager -> opportunity_supervisor',
            'profile_manager -> alerts (on degradation)',
        ],
    }
    run.save(update_fields=['status', 'regime', 'runtime_mode', 'readiness_status', 'safety_status', 'finished_at', 'summary', 'details', 'updated_at'])
    return run


def build_profile_governance_summary() -> dict:
    latest_run = ProfileGovernanceRun.objects.select_related('decision').order_by('-started_at', '-id').first()
    decision = latest_run.decision if latest_run and hasattr(latest_run, 'decision') else None

    return {
        'latest_run': latest_run.id if latest_run else None,
        'current_regime': latest_run.regime if latest_run else 'NORMAL',
        'decision_mode': decision.decision_mode if decision else '',
        'is_applied': bool(decision and decision.is_applied),
        'target_profiles': {
            'research_agent': decision.target_research_profile if decision else '',
            'signals': decision.target_signal_profile if decision else '',
            'opportunity_supervisor': decision.target_opportunity_supervisor_profile if decision else '',
            'mission_control': decision.target_mission_control_profile if decision else '',
            'portfolio_governor': decision.target_portfolio_governor_profile if decision else '',
        },
        'blocking_constraints': decision.blocking_constraints if decision else [],
        'reason_codes': decision.reason_codes if decision else [],
        'runtime_mode': latest_run.runtime_mode if latest_run else 'UNKNOWN',
        'readiness_status': latest_run.readiness_status if latest_run else 'UNKNOWN',
        'safety_status': latest_run.safety_status if latest_run else 'UNKNOWN',
        'paper_demo_only': True,
        'real_execution_enabled': False,
    }

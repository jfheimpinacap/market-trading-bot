from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.learning_memory.services import run_learning_rebuild
from apps.memory_retrieval.services import run_indexing
from apps.champion_challenger.services import run_shadow_benchmark
from apps.execution_simulator.services import run_execution_lifecycle
from apps.mission_control.models import (
    MissionControlCycle,
    MissionControlCycleStatus,
    MissionControlSession,
    MissionControlSessionStatus,
    MissionControlStep,
    MissionControlStepStatus,
)
from apps.notification_center.services import run_automatic_dispatch
from apps.notification_center.services.scheduler import run_digest_cycle
from apps.operator_alerts.services import rebuild_operator_alerts
from apps.opportunity_supervisor.services import run_opportunity_cycle
from apps.postmortem_agents.services.board import run_postmortem_board
from apps.postmortem_demo.models import TradeReview
from apps.position_manager.services import run_position_lifecycle
from apps.portfolio_governor.services import run_portfolio_governance
from apps.profile_manager.services import get_effective_profile_targets, run_profile_governance
from apps.research_agent.services.scan import run_full_research_scan
from apps.research_agent.services.universe_scan import run_universe_scan
from apps.risk_agent.services import run_position_watch
from apps.runtime_governor.services import get_capabilities_for_current_mode, get_runtime_state
from apps.safety_guard.services import get_safety_status


@dataclass
class CycleDecision:
    status: str
    reason: str


def _should_run(cycle_number: int, every_n: int | None) -> bool:
    if every_n is None:
        return False
    every_n = int(every_n)
    return every_n > 0 and cycle_number % every_n == 0


def _record_step(cycle: MissionControlCycle, *, step_type: str, fn, details: dict | None = None):
    step = MissionControlStep.objects.create(cycle=cycle, step_type=step_type, status=MissionControlStepStatus.SUCCESS, started_at=timezone.now())
    payload = details or {}
    try:
        result = fn()
        step.summary = f'{step_type} completed.'
        step.details = {**payload, 'result': _serialize_result(result)}
    except Exception as exc:
        step.status = MissionControlStepStatus.FAILED
        step.summary = f'{step_type} failed: {exc}'
        step.details = {**payload, 'error': str(exc)}
    step.finished_at = timezone.now()
    step.save(update_fields=['status', 'summary', 'details', 'finished_at', 'updated_at'])
    return step


def _serialize_result(result):
    if result is None:
        return None
    if hasattr(result, 'id'):
        data = {'id': result.id}
        for field in ('status', 'summary', 'cycle_number', 'opportunities_built', 'proposals_generated', 'queued_count', 'auto_executed_count', 'blocked_count'):
            if hasattr(result, field):
                data[field] = getattr(result, field)
        return data
    if isinstance(result, dict):
        return result
    return str(result)


def evaluate_cycle_allowed() -> CycleDecision:
    runtime_caps = get_capabilities_for_current_mode()
    safety = get_safety_status()
    if safety['kill_switch_enabled'] or safety['hard_stop_active']:
        return CycleDecision(status=MissionControlCycleStatus.SKIPPED, reason='Safety hard block active.')
    allow_opportunity = bool(runtime_caps.get('allow_proposals', False) and runtime_caps.get('allow_signal_generation', False))
    if not allow_opportunity:
        return CycleDecision(status=MissionControlCycleStatus.SKIPPED, reason='Runtime mode blocks opportunity supervisor execution.')
    return CycleDecision(status=MissionControlCycleStatus.SUCCESS, reason='Allowed')


def run_mission_control_cycle(*, session: MissionControlSession, settings: dict) -> MissionControlCycle:
    decision = evaluate_cycle_allowed()
    cycle = MissionControlCycle.objects.create(
        session=session,
        cycle_number=session.cycle_count + 1,
        status=decision.status,
        started_at=timezone.now(),
        details={
            'settings': settings,
            'runtime': {'mode': get_runtime_state().current_mode},
            'safety': get_safety_status(),
            'gating_reason': decision.reason,
            'precedent_aware_mode': True,
        },
    )
    if decision.status == MissionControlCycleStatus.SKIPPED:
        cycle.summary = decision.reason
        cycle.finished_at = timezone.now()
        cycle.save(update_fields=['summary', 'finished_at', 'updated_at'])
        session.cycle_count += 1
        session.last_cycle_at = cycle.finished_at
        session.status = MissionControlSessionStatus.DEGRADED
        session.summary = decision.reason
        session.save(update_fields=['cycle_count', 'last_cycle_at', 'status', 'summary', 'updated_at'])
        return cycle

    profile_governance_step = _record_step(
        cycle,
        step_type='profile_governance_check',
        fn=lambda: run_profile_governance(triggered_by='mission_control'),
    )
    profile_result = (profile_governance_step.details or {}).get('result') or {}
    current_targets = get_effective_profile_targets()

    run_every_research = settings.get('run_research_every_n_cycles')
    run_every_universe = settings.get('run_universe_scan_every_n_cycles')
    research_profile = current_targets.get('target_research_profile') or settings.get('universe_filter_profile', 'balanced_scan')
    opportunity_profile = current_targets.get('target_opportunity_supervisor_profile') or settings.get('opportunity_profile_slug')
    portfolio_profile = current_targets.get('target_portfolio_governor_profile')

    if _should_run(cycle.cycle_number, run_every_research):
        _record_step(cycle, step_type='research_scan', fn=lambda: run_full_research_scan(source_ids=settings.get('research_source_ids')))

    if _should_run(cycle.cycle_number, run_every_universe):
        _record_step(cycle, step_type='universe_scan', fn=lambda: run_universe_scan(filter_profile=research_profile))
    if _should_run(cycle.cycle_number, settings.get('run_memory_index_refresh_every_n_cycles')):
        _record_step(cycle, step_type='memory_index_refresh', fn=lambda: run_indexing(sources=['learning', 'postmortem'], force_reembed=False))

    _record_step(
        cycle,
        step_type='portfolio_governance_check',
        fn=lambda: run_portfolio_governance(profile_slug=portfolio_profile, triggered_by='mission_control'),
        details={'meta_governance': profile_result},
    )

    opportunity_step = _record_step(
        cycle,
        step_type='opportunity_cycle',
        fn=lambda: run_opportunity_cycle(profile_slug=opportunity_profile, triggered_by='mission_control'),
        details={'meta_governance': profile_result},
    )

    result = (opportunity_step.details or {}).get('result') or {}
    cycle.opportunities_built = int(result.get('opportunities_built') or 0)
    cycle.proposals_generated = int(result.get('proposals_generated') or 0)
    cycle.queue_count = int(result.get('queued_count') or 0)
    cycle.auto_execute_count = int(result.get('auto_executed_count') or 0)
    cycle.blocked_count = int(result.get('blocked_count') or 0)

    if settings.get('run_watch_every_cycle', True):
        _record_step(cycle, step_type='risk_watch', fn=lambda: run_position_watch(metadata={'triggered_from': 'mission_control'}))
    if settings.get('run_position_lifecycle_every_cycle', True):
        _record_step(cycle, step_type='position_lifecycle_check', fn=lambda: run_position_lifecycle(metadata={'triggered_from': 'mission_control'}))

    _record_step(cycle, step_type='execution_lifecycle_step', fn=lambda: run_execution_lifecycle(open_only=True, metadata={'triggered_from': 'mission_control'}))
    _record_step(cycle, step_type='pending_order_review_step', fn=lambda: run_execution_lifecycle(open_only=True, metadata={'triggered_from': 'mission_control', 'pending_review': True}))

    _record_step(cycle, step_type='alerts_rebuild', fn=rebuild_operator_alerts)
    _record_step(cycle, step_type='notifications_dispatch', fn=run_automatic_dispatch)

    if _should_run(cycle.cycle_number, settings.get('run_digest_every_n_cycles')):
        _record_step(cycle, step_type='digest_cycle', fn=run_digest_cycle)

    if _should_run(cycle.cycle_number, settings.get('run_postmortem_every_n_cycles')):
        latest_review = TradeReview.objects.order_by('-created_at').first()
        if latest_review:
            _record_step(cycle, step_type='postmortem_board_refresh', fn=lambda: run_postmortem_board(related_trade_review_id=latest_review.id))

    if _should_run(cycle.cycle_number, settings.get('run_learning_rebuild_every_n_cycles')):
        _record_step(cycle, step_type='learning_rebuild', fn=lambda: run_learning_rebuild(triggered_from='automation'))

    if _should_run(cycle.cycle_number, settings.get('run_shadow_benchmark_every_n_cycles')):
        _record_step(
            cycle,
            step_type='champion_challenger_shadow_benchmark',
            fn=lambda: run_shadow_benchmark(payload={'lookback_hours': settings.get('shadow_benchmark_lookback_hours', 24)}),
        )

    cycle.steps_run_count = cycle.steps.count()
    any_failed = cycle.steps.filter(status=MissionControlStepStatus.FAILED).exists()
    cycle.status = MissionControlCycleStatus.PARTIAL if any_failed else MissionControlCycleStatus.SUCCESS
    cycle.finished_at = timezone.now()
    cycle.summary = (
        f'Cycle {cycle.cycle_number} {cycle.status}: steps={cycle.steps_run_count}, opps={cycle.opportunities_built}, '
        f'queue={cycle.queue_count}, auto={cycle.auto_execute_count}, blocked={cycle.blocked_count}.'
    )
    cycle.save(update_fields=[
        'steps_run_count',
        'opportunities_built',
        'proposals_generated',
        'queue_count',
        'auto_execute_count',
        'blocked_count',
        'status',
        'summary',
        'finished_at',
        'updated_at',
    ])

    session.cycle_count += 1
    session.last_cycle_at = cycle.finished_at
    session.status = MissionControlSessionStatus.DEGRADED if any_failed else MissionControlSessionStatus.RUNNING
    session.summary = cycle.summary
    session.save(update_fields=['cycle_count', 'last_cycle_at', 'status', 'summary', 'updated_at'])
    return cycle

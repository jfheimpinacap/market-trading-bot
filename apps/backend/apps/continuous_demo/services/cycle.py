from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.automation_demo.models import DemoAutomationRun
from apps.automation_demo.services import run_demo_cycle
from apps.continuous_demo.models import ContinuousDemoCycleRun, ContinuousDemoSession, CycleStatus, SessionStatus
from apps.continuous_demo.services.control import get_runtime_control
from apps.learning_memory.models import LearningRebuildRun
from apps.learning_memory.services import run_learning_rebuild, should_rebuild_learning
from apps.paper_trading.services.portfolio import get_active_account
from apps.paper_trading.services.valuation import revalue_account
from apps.postmortem_demo.services import generate_trade_reviews
from apps.real_data_sync.services import run_provider_sync
from apps.real_market_ops.services import RunOptions as RealOpsRunOptions, run_real_market_operation
from apps.runtime_governor.services import get_capabilities_for_current_mode, reconcile_runtime_state
from apps.semi_auto_demo.services.orchestration import RunOptions, run_scan_and_execute
from apps.safety_guard.models import SafetyEventSource
from apps.safety_guard.services import evaluate_cycle_health


def _cycle_summary(*, cycle: ContinuousDemoCycleRun) -> str:
    return (
        f'Cycle {cycle.cycle_number} {cycle.status}: proposals={cycle.proposals_generated}, '
        f'auto={cycle.auto_executed_count}, pending={cycle.approval_required_count}, blocked={cycle.blocked_count}.'
    )


@transaction.atomic
def _begin_cycle(session: ContinuousDemoSession) -> ContinuousDemoCycleRun:
    control = get_runtime_control()
    if control.cycle_in_progress:
        raise ValueError('A continuous demo cycle is already in progress.')

    control.cycle_in_progress = True
    control.last_error = ''
    control.save(update_fields=['cycle_in_progress', 'last_error', 'updated_at'])

    return ContinuousDemoCycleRun.objects.create(
        session=session,
        cycle_number=session.total_cycles + 1,
        status=CycleStatus.SUCCESS,
        started_at=timezone.now(),
        actions_run=[],
        details={},
    )


@transaction.atomic
def _finish_cycle(*, session: ContinuousDemoSession, cycle: ContinuousDemoCycleRun, error: str | None = None) -> ContinuousDemoCycleRun:
    control = get_runtime_control()
    control.cycle_in_progress = False
    if error:
        control.last_error = error
    control.save(update_fields=['cycle_in_progress', 'last_error', 'updated_at'])

    session.last_cycle_at = cycle.finished_at
    session.total_cycles += 1
    session.total_auto_executed += cycle.auto_executed_count
    session.total_pending_approvals += cycle.approval_required_count
    session.total_blocked += cycle.blocked_count
    if cycle.status in {CycleStatus.FAILED, CycleStatus.PARTIAL}:
        session.total_errors += 1
        if cycle.status == CycleStatus.FAILED:
            session.session_status = SessionStatus.FAILED
    session.summary = cycle.summary
    session.save(update_fields=[
        'last_cycle_at',
        'total_cycles',
        'total_auto_executed',
        'total_pending_approvals',
        'total_blocked',
        'total_errors',
        'session_status',
        'summary',
        'updated_at',
    ])
    return cycle


def run_single_cycle(*, session: ContinuousDemoSession, settings: dict) -> ContinuousDemoCycleRun:
    reconcile_runtime_state(reason='Continuous demo requested reconciliation before cycle.')
    runtime_caps = get_capabilities_for_current_mode()
    if not runtime_caps['allow_continuous_loop']:
        raise ValueError('Runtime mode blocks continuous loop execution.')

    cycle = _begin_cycle(session)
    error_message: str | None = None
    try:
        real_sync_runs: list[dict] = []
        refresh_enabled = bool(settings.get('real_data_refresh_enabled', False))
        refresh_every = max(1, int(settings.get('real_data_refresh_every_n_cycles', 5)))
        if refresh_enabled and cycle.cycle_number % refresh_every == 0:
            for provider in ('kalshi', 'polymarket'):
                sync_run = run_provider_sync(
                    provider=provider,
                    sync_type='active_only',
                    active_only=bool(settings.get('real_data_refresh_active_only', True)),
                    limit=max(1, int(settings.get('real_data_refresh_limit', 50))),
                    triggered_from='continuous_demo',
                )
                real_sync_runs.append({'provider': provider, 'run_id': sync_run.id, 'status': sync_run.status})

        automation_run = run_demo_cycle(triggered_from=DemoAutomationRun.TriggeredFrom.API)
        use_real_scope = bool(settings.get('use_real_market_scope', False)) and str(settings.get('market_scope', 'mixed')) == 'real_only'
        if use_real_scope:
            real_ops_run = run_real_market_operation(
                options=RealOpsRunOptions(execute_auto=True, triggered_from='continuous_demo')
            )
            actions_run = [
                {'action': 'automation_demo.run_demo_cycle', 'run_id': automation_run.id, 'status': automation_run.status},
                {'action': 'real_market_ops.run_real_market_operation', 'run_id': real_ops_run.id, 'status': real_ops_run.status},
            ]
            evaluated = real_ops_run.markets_considered
            proposals = real_ops_run.proposals_generated
            auto_count = real_ops_run.auto_executed_count
            approval_count = real_ops_run.approval_required_count
            blocked_count = real_ops_run.blocked_count
            cycle_state = CycleStatus.SUCCESS if real_ops_run.status == 'SUCCESS' else CycleStatus.PARTIAL
        else:
            semi_auto_run = run_scan_and_execute(
                options=RunOptions(
                    market_limit=int(settings.get('market_limit_per_cycle', 8)),
                    market_scope=str(settings.get('market_scope', 'mixed')),
                    max_auto_trades_per_run=min(
                        int(settings.get('max_auto_trades_per_cycle', 2)),
                        int(runtime_caps['max_auto_trades_per_cycle'] or 0),
                    ) if runtime_caps['allow_auto_execution'] else 0,
                )
            )
            actions_run = [
                {'action': 'automation_demo.run_demo_cycle', 'run_id': automation_run.id, 'status': automation_run.status},
                {'action': 'semi_auto_demo.run_scan_and_execute', 'run_id': semi_auto_run.id, 'status': semi_auto_run.status},
            ]
            evaluated = semi_auto_run.markets_evaluated
            proposals = semi_auto_run.proposals_generated
            auto_count = semi_auto_run.auto_executed_count
            approval_count = semi_auto_run.approval_required_count
            blocked_count = semi_auto_run.blocked_count
            cycle_state = CycleStatus.SUCCESS if semi_auto_run.status == 'SUCCESS' else CycleStatus.PARTIAL


        extra = {}
        if settings.get('revalue_after_trade', True) and auto_count > 0:
            account = get_active_account()
            revalue_account(account, create_snapshot=True)
            extra['revalue_after_trade'] = True

        if settings.get('review_after_trade', True) and auto_count > 0:
            review_results = generate_trade_reviews(refresh_existing=True)
            extra['reviews_processed'] = len(review_results)
        else:
            review_results = []

        should_rebuild, rebuild_reason = should_rebuild_learning(
            settings=settings,
            cycle_number=cycle.cycle_number,
            reviews_generated=bool(review_results),
        )
        if should_rebuild:
            rebuild_run = run_learning_rebuild(
                triggered_from=LearningRebuildRun.TriggeredFrom.CONTINUOUS_DEMO,
                related_session_id=session.id,
                related_cycle_id=cycle.id,
            )
            extra['learning_rebuild'] = {
                'run_id': rebuild_run.id,
                'status': rebuild_run.status,
                'summary': rebuild_run.summary,
            }
        else:
            extra['learning_rebuild'] = {'triggered': False, 'reason': rebuild_reason}

        cycle.actions_run = actions_run
        cycle.markets_evaluated = evaluated
        cycle.proposals_generated = proposals
        cycle.auto_executed_count = auto_count
        cycle.approval_required_count = approval_count
        cycle.blocked_count = blocked_count
        cycle.status = cycle_state
        cycle.details = {
            'automation_run': {'id': automation_run.id, 'status': automation_run.status, 'summary': automation_run.summary},
            'semi_auto_run': {'id': semi_auto_run.id, 'status': semi_auto_run.status, 'summary': semi_auto_run.summary} if not use_real_scope else None,
            'real_market_ops_run': {'id': real_ops_run.id, 'status': real_ops_run.status, 'summary': real_ops_run.summary} if use_real_scope else None,
            'real_data_sync_runs': real_sync_runs,
            'settings_applied': settings,
            'runtime_caps': runtime_caps,
            **extra,
        }
    except Exception as exc:
        error_message = str(exc)
        cycle.status = CycleStatus.FAILED
        cycle.details = {'error': error_message, 'settings_applied': settings}

    cycle.finished_at = timezone.now()
    cycle.summary = _cycle_summary(cycle=cycle)
    cycle.save(update_fields=[
        'actions_run',
        'markets_evaluated',
        'proposals_generated',
        'auto_executed_count',
        'approval_required_count',
        'blocked_count',
        'status',
        'summary',
        'details',
        'finished_at',
        'updated_at',
    ])
    cycle = _finish_cycle(session=session, cycle=cycle, error=error_message)
    evaluate_cycle_health(cycle=cycle, source=SafetyEventSource.CONTINUOUS_DEMO)
    return cycle

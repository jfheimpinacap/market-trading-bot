from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.automation_demo.models import DemoAutomationRun
from apps.automation_demo.services import run_demo_cycle
from apps.continuous_demo.models import ContinuousDemoCycleRun, ContinuousDemoSession, CycleStatus, SessionStatus
from apps.continuous_demo.services.control import get_runtime_control
from apps.paper_trading.services.portfolio import get_active_account
from apps.paper_trading.services.valuation import revalue_account
from apps.postmortem_demo.services import generate_trade_reviews
from apps.semi_auto_demo.services.orchestration import RunOptions, run_scan_and_execute


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
    cycle = _begin_cycle(session)
    error_message: str | None = None
    try:
        automation_run = run_demo_cycle(triggered_from=DemoAutomationRun.TriggeredFrom.API)
        semi_auto_run = run_scan_and_execute(
            options=RunOptions(
                market_limit=int(settings.get('market_limit_per_cycle', 8)),
                market_scope=str(settings.get('market_scope', 'mixed')),
                max_auto_trades_per_run=int(settings.get('max_auto_trades_per_cycle', 2)),
            )
        )

        actions_run = [
            {'action': 'automation_demo.run_demo_cycle', 'run_id': automation_run.id, 'status': automation_run.status},
            {'action': 'semi_auto_demo.run_scan_and_execute', 'run_id': semi_auto_run.id, 'status': semi_auto_run.status},
        ]

        extra = {}
        if settings.get('revalue_after_trade', True) and semi_auto_run.auto_executed_count > 0:
            account = get_active_account()
            revalue_account(account, create_snapshot=True)
            extra['revalue_after_trade'] = True

        if settings.get('review_after_trade', True) and semi_auto_run.auto_executed_count > 0:
            review_results = generate_trade_reviews(refresh_existing=True)
            extra['reviews_processed'] = len(review_results)

        cycle.actions_run = actions_run
        cycle.markets_evaluated = semi_auto_run.markets_evaluated
        cycle.proposals_generated = semi_auto_run.proposals_generated
        cycle.auto_executed_count = semi_auto_run.auto_executed_count
        cycle.approval_required_count = semi_auto_run.approval_required_count
        cycle.blocked_count = semi_auto_run.blocked_count
        cycle.status = CycleStatus.SUCCESS if semi_auto_run.status == 'SUCCESS' else CycleStatus.PARTIAL
        cycle.details = {
            'automation_run': {'id': automation_run.id, 'status': automation_run.status, 'summary': automation_run.summary},
            'semi_auto_run': {'id': semi_auto_run.id, 'status': semi_auto_run.status, 'summary': semi_auto_run.summary},
            'settings_applied': settings,
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
    return _finish_cycle(session=session, cycle=cycle, error=error_message)

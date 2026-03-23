from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable

from django.utils import timezone

from apps.automation_demo.models import DemoAutomationRun
from apps.markets.models import Market, MarketSnapshot
from apps.markets.simulation import MarketSimulationEngine
from apps.paper_trading.models import PaperTrade
from apps.paper_trading.services.portfolio import get_active_account
from apps.paper_trading.services.valuation import revalue_account
from apps.postmortem_demo.models import TradeReview
from apps.postmortem_demo.services import generate_trade_reviews
from apps.signals.models import MarketSignal
from apps.signals.services import generate_demo_signals


STEP_STATUS_SUCCESS = 'SUCCESS'
STEP_STATUS_FAILED = 'FAILED'
STEP_STATUS_SKIPPED = 'SKIPPED'


@dataclass
class StepExecutionResult:
    step_name: str
    status: str
    summary: str
    metadata: dict


@dataclass
class ActionExecutionResult:
    action_type: str
    status: str
    summary: str
    details: dict


def _simulation_step() -> StepExecutionResult:
    started_at = timezone.now()
    result = MarketSimulationEngine().run_tick(now=started_at)
    return StepExecutionResult(
        step_name=DemoAutomationRun.ActionType.SIMULATE_TICK,
        status=STEP_STATUS_SUCCESS,
        summary=(
            f'Simulated {result.processed} markets, updated {result.updated}, '
            f'skipped {result.skipped}, and created {result.snapshots_created} snapshots.'
        ),
        metadata={
            'processed': result.processed,
            'updated': result.updated,
            'skipped': result.skipped,
            'snapshots_created': result.snapshots_created,
            'state_changes': result.state_changes,
            'started_at': started_at.isoformat(),
        },
    )


def _signals_step() -> StepExecutionResult:
    result = generate_demo_signals()
    return StepExecutionResult(
        step_name=DemoAutomationRun.ActionType.GENERATE_SIGNALS,
        status=STEP_STATUS_SUCCESS,
        summary=(
            f'Generated {result.signals_created} demo signals, updated {result.signals_updated}, '
            f'and evaluated {result.markets_evaluated} markets.'
        ),
        metadata={
            'markets_evaluated': result.markets_evaluated,
            'signals_created': result.signals_created,
            'signals_updated': result.signals_updated,
            'signal_run_id': result.run.id,
            'signal_run_status': result.run.status,
            'signal_run_finished_at': result.run.finished_at.isoformat() if result.run.finished_at else None,
        },
    )


def _revalue_step() -> StepExecutionResult:
    account = get_active_account()
    snapshot_count_before = account.snapshots.count()
    revalue_account(account, create_snapshot=True)
    account.refresh_from_db()
    return StepExecutionResult(
        step_name=DemoAutomationRun.ActionType.REVALUE_PORTFOLIO,
        status=STEP_STATUS_SUCCESS,
        summary=(
            f'Revalued demo portfolio for {account.slug}. Equity is now {account.equity} '
            f'with {account.positions.filter(status="OPEN", quantity__gt=0).count()} open positions.'
        ),
        metadata={
            'account_id': account.id,
            'account_slug': account.slug,
            'equity': str(account.equity),
            'cash_balance': str(account.cash_balance),
            'open_positions_count': account.positions.filter(status='OPEN', quantity__gt=0).count(),
            'snapshot_count_before': snapshot_count_before,
            'snapshot_count_after': account.snapshots.count(),
        },
    )


def _reviews_step() -> StepExecutionResult:
    results = generate_trade_reviews(refresh_existing=True)
    created_count = sum(1 for item in results if item.created)
    refreshed_count = sum(1 for item in results if not item.created)
    stale_marked_count = sum(1 for item in results if item.stale_marked)
    summary = (
        'No executed paper trades were available for demo review generation.'
        if not results
        else f'Generated or refreshed {len(results)} trade reviews ({created_count} created, {refreshed_count} refreshed).'
    )
    return StepExecutionResult(
        step_name=DemoAutomationRun.ActionType.GENERATE_TRADE_REVIEWS,
        status=STEP_STATUS_SUCCESS,
        summary=summary,
        metadata={
            'reviews_processed': len(results),
            'reviews_created': created_count,
            'reviews_refreshed': refreshed_count,
            'reviews_marked_stale': stale_marked_count,
            'review_ids': [item.review.id for item in results],
        },
    )


def _sync_state_step() -> StepExecutionResult:
    account = get_active_account()
    return StepExecutionResult(
        step_name=DemoAutomationRun.ActionType.SYNC_DEMO_STATE,
        status=STEP_STATUS_SUCCESS,
        summary='Collected a fresh local summary of markets, signals, paper trades, portfolio, and trade reviews.',
        metadata={
            'markets_count': Market.objects.count(),
            'market_snapshots_count': MarketSnapshot.objects.count(),
            'signals_count': MarketSignal.objects.count(),
            'paper_trades_count': PaperTrade.objects.count(),
            'trade_reviews_count': TradeReview.objects.count(),
            'account_id': account.id,
            'account_equity': str(account.equity),
            'account_updated_at': account.updated_at.isoformat(),
        },
    )


ACTION_HANDLERS: dict[str, Callable[[], StepExecutionResult]] = {
    DemoAutomationRun.ActionType.SIMULATE_TICK: _simulation_step,
    DemoAutomationRun.ActionType.GENERATE_SIGNALS: _signals_step,
    DemoAutomationRun.ActionType.REVALUE_PORTFOLIO: _revalue_step,
    DemoAutomationRun.ActionType.GENERATE_TRADE_REVIEWS: _reviews_step,
    DemoAutomationRun.ActionType.SYNC_DEMO_STATE: _sync_state_step,
}


CYCLE_STEP_ORDER = [
    DemoAutomationRun.ActionType.SIMULATE_TICK,
    DemoAutomationRun.ActionType.GENERATE_SIGNALS,
    DemoAutomationRun.ActionType.REVALUE_PORTFOLIO,
    DemoAutomationRun.ActionType.GENERATE_TRADE_REVIEWS,
]


def _serialize_step(step: StepExecutionResult) -> dict:
    return asdict(step)


def _run_action_handler(action_type: str) -> ActionExecutionResult:
    handler = ACTION_HANDLERS[action_type]
    step = handler()
    return ActionExecutionResult(
        action_type=action_type,
        status=DemoAutomationRun.Status.SUCCESS,
        summary=step.summary,
        details={'steps': [_serialize_step(step)], 'result': step.metadata},
    )


def execute_demo_action(*, action_type: str, triggered_from: str = DemoAutomationRun.TriggeredFrom.API) -> DemoAutomationRun:
    started_at = timezone.now()
    run = DemoAutomationRun.objects.create(
        action_type=action_type,
        status=DemoAutomationRun.Status.RUNNING,
        summary='',
        details={},
        triggered_from=triggered_from,
        started_at=started_at,
    )

    try:
        result = _run_action_handler(action_type)
        run.status = result.status
        run.summary = result.summary
        run.details = {
            **result.details,
            'action_type': action_type,
        }
    except Exception as exc:
        run.status = DemoAutomationRun.Status.FAILED
        run.summary = f'{action_type} failed: {exc}'
        run.details = {
            'action_type': action_type,
            'error': str(exc),
            'steps': [
                {
                    'step_name': action_type,
                    'status': STEP_STATUS_FAILED,
                    'summary': str(exc),
                    'metadata': {},
                }
            ],
        }
    run.finished_at = timezone.now()
    run.save(update_fields=['status', 'summary', 'details', 'finished_at', 'updated_at'])
    return run


def run_demo_cycle(*, triggered_from: str = DemoAutomationRun.TriggeredFrom.API) -> DemoAutomationRun:
    started_at = timezone.now()
    run = DemoAutomationRun.objects.create(
        action_type=DemoAutomationRun.ActionType.RUN_DEMO_CYCLE,
        status=DemoAutomationRun.Status.RUNNING,
        summary='',
        details={'steps': []},
        triggered_from=triggered_from,
        started_at=started_at,
    )

    step_results: list[dict] = []
    completed_steps = 0
    total_steps = len(CYCLE_STEP_ORDER)
    failure_message: str | None = None

    for index, step_name in enumerate(CYCLE_STEP_ORDER):
        try:
            step = ACTION_HANDLERS[step_name]()
            step_results.append(_serialize_step(step))
            completed_steps += 1
        except Exception as exc:
            failure_message = f'{step_name} failed: {exc}'
            step_results.append(
                {
                    'step_name': step_name,
                    'status': STEP_STATUS_FAILED,
                    'summary': failure_message,
                    'metadata': {},
                }
            )
            for skipped_step_name in CYCLE_STEP_ORDER[index + 1 :]:
                step_results.append(
                    {
                        'step_name': skipped_step_name,
                        'status': STEP_STATUS_SKIPPED,
                        'summary': f'{skipped_step_name} was not executed because an earlier step failed.',
                        'metadata': {},
                    }
                )
            break

    if failure_message:
        run.status = DemoAutomationRun.Status.PARTIAL if completed_steps > 0 else DemoAutomationRun.Status.FAILED
        run.summary = (
            f'Demo cycle completed {completed_steps} of {total_steps} steps before stopping. '
            f'Last error: {failure_message}'
        )
    else:
        run.status = DemoAutomationRun.Status.SUCCESS
        run.summary = f'Demo cycle completed all {total_steps} steps successfully.'

    run.finished_at = timezone.now()
    run.details = {
        'action_type': DemoAutomationRun.ActionType.RUN_DEMO_CYCLE,
        'overall_status': run.status,
        'completed_steps': completed_steps,
        'total_steps': total_steps,
        'steps': step_results,
        'error': failure_message,
    }
    run.save(update_fields=['status', 'summary', 'details', 'finished_at', 'updated_at'])
    return run


def get_automation_summary() -> dict:
    recent_runs = list(DemoAutomationRun.objects.order_by('-started_at', '-id')[:20])
    latest_run = recent_runs[0] if recent_runs else None
    actions = [
        DemoAutomationRun.ActionType.SIMULATE_TICK,
        DemoAutomationRun.ActionType.GENERATE_SIGNALS,
        DemoAutomationRun.ActionType.REVALUE_PORTFOLIO,
        DemoAutomationRun.ActionType.GENERATE_TRADE_REVIEWS,
        DemoAutomationRun.ActionType.SYNC_DEMO_STATE,
        DemoAutomationRun.ActionType.RUN_DEMO_CYCLE,
    ]
    last_by_action: dict[str, DemoAutomationRun | None] = {}
    for action in actions:
        last_by_action[action] = next((run for run in recent_runs if run.action_type == action), None)

    return {
        'recent_runs_count': len(recent_runs),
        'available_actions': [
            {
                'action_type': DemoAutomationRun.ActionType.SIMULATE_TICK,
                'label': 'Run simulation tick',
                'description': 'Advances the local market simulation by one safe demo tick.',
            },
            {
                'action_type': DemoAutomationRun.ActionType.GENERATE_SIGNALS,
                'label': 'Generate signals',
                'description': 'Refreshes mock-agent demo signals from local market state only.',
            },
            {
                'action_type': DemoAutomationRun.ActionType.REVALUE_PORTFOLIO,
                'label': 'Revalue portfolio',
                'description': 'Marks the active demo paper portfolio to the latest local market prices.',
            },
            {
                'action_type': DemoAutomationRun.ActionType.GENERATE_TRADE_REVIEWS,
                'label': 'Generate trade reviews',
                'description': 'Creates or refreshes local post-mortem reviews for executed demo trades.',
            },
            {
                'action_type': DemoAutomationRun.ActionType.SYNC_DEMO_STATE,
                'label': 'Sync demo state',
                'description': 'Collects a lightweight derived summary without running any trade action.',
            },
            {
                'action_type': DemoAutomationRun.ActionType.RUN_DEMO_CYCLE,
                'label': 'Run full demo cycle',
                'description': 'Runs simulation, signals, portfolio revalue, and trade review generation in order.',
            },
        ],
        'latest_run': latest_run,
        'last_by_action': last_by_action,
    }

from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.allocation_engine.services import AllocationConfig, evaluate_allocation
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.valuation import revalue_account
from apps.policy_engine.models import ApprovalDecisionType
from apps.proposal_engine.services import generate_trade_proposal
from apps.replay_lab.models import ReplayRun, ReplayRunStatus, ReplayStep
from apps.replay_lab.services.execution import activate_replay_account, create_replay_account, snapshot_replay_account, summarize_account
from apps.replay_lab.services.timeline import build_replay_timeline
from apps.safety_guard.models import SafetyEventSource
from apps.safety_guard.services.evaluation import evaluate_auto_execution


@dataclass
class ReplayResult:
    run: ReplayRun


def _json_safe_config(config: dict) -> dict:
    payload = {}
    for key, value in config.items():
        if hasattr(value, 'isoformat'):
            payload[key] = value.isoformat()
        else:
            payload[key] = value
    return payload


def run_replay(*, config: dict) -> ReplayResult:
    run = ReplayRun.objects.create(
        status=ReplayRunStatus.RUNNING,
        source_scope=config['source_scope'],
        provider_scope=config.get('provider_scope') or 'all',
        replay_start_at=config['start_timestamp'],
        replay_end_at=config['end_timestamp'],
        started_at=timezone.now(),
        details={'config': _json_safe_config(config), 'errors': []},
    )

    account = create_replay_account(replay_run_id=run.id)
    run.paper_account = account
    run.save(update_fields=['paper_account', 'updated_at'])

    timeline = build_replay_timeline(config=config)
    if not timeline:
        run.status = ReplayRunStatus.FAILED
        run.finished_at = timezone.now()
        run.summary = 'No snapshots found for the selected range. Sync real market data first to build a usable historical replay.'
        run.details = {**run.details, 'error': 'insufficient_snapshots'}
        run.save(update_fields=['status', 'finished_at', 'summary', 'details', 'updated_at'])
        return ReplayResult(run=run)

    try:
        with activate_replay_account(account):
            for index, step in enumerate(timeline, start=1):
                proposals = []
                trades_executed = 0
                approvals_required = 0
                blocked = 0
                errors = []

                for snapshot in step.snapshots:
                    market = snapshot.market
                    market.current_market_probability = snapshot.market_probability
                    market.current_yes_price = snapshot.yes_price
                    market.current_no_price = snapshot.no_price
                    market.liquidity = snapshot.liquidity
                    market.volume_24h = snapshot.volume_24h

                    proposal = generate_trade_proposal(market=market, paper_account=account, triggered_from='automation')
                    if not config.get('use_learning_adjustments', True):
                        proposal.metadata = {**proposal.metadata, 'learning_adjustments_disabled_for_replay': True}
                        proposal.save(update_fields=['metadata', 'updated_at'])
                    proposals.append(proposal)

                allocation_map = {}
                if proposals and config.get('use_allocation', True):
                    allocation_snapshot = evaluate_allocation(
                        scope_type=config['source_scope'] if config['source_scope'] in {'real_only', 'demo_only'} else 'mixed',
                        triggered_from='replay_lab',
                        proposals=proposals,
                        persist=True,
                        config=AllocationConfig(max_candidates_considered=len(proposals), max_executions_per_run=max(1, len(proposals))),
                    )
                    allocation_map = {item['proposal'].id: item for item in allocation_snapshot['details']}
                for proposal in proposals:
                    run.proposals_generated += 1
                    if proposal.policy_decision == ApprovalDecisionType.HARD_BLOCK:
                        blocked += 1
                        run.blocked_count += 1
                        continue
                    if proposal.policy_decision == ApprovalDecisionType.APPROVAL_REQUIRED:
                        approvals_required += 1
                        run.approvals_required += 1
                        if config.get('treat_approval_required_as_skip', True):
                            continue

                    allocation_item = allocation_map.get(proposal.id)
                    if allocation_item and allocation_item['decision'] not in {'SELECTED', 'REDUCED'}:
                        blocked += 1
                        run.blocked_count += 1
                        continue

                    if not config.get('auto_execute_allowed', True):
                        continue
                    if not (proposal.suggested_side and proposal.suggested_quantity and proposal.suggested_trade_type in {'BUY', 'SELL'}):
                        blocked += 1
                        run.blocked_count += 1
                        continue

                    safety = evaluate_auto_execution(proposal=proposal, auto_trades_so_far=trades_executed, source=SafetyEventSource.AUTOMATION_DEMO)
                    if not safety.allowed:
                        blocked += 1
                        run.blocked_count += 1
                        continue

                    quantity = allocation_item['final_allocated_quantity'] if allocation_item else proposal.suggested_quantity
                    try:
                        execute_paper_trade(
                            market=proposal.market,
                            trade_type=proposal.suggested_trade_type,
                            side=proposal.suggested_side,
                            quantity=quantity,
                            account=account,
                            notes='Historical replay demo execution.',
                            metadata={'replay_run_id': run.id, 'replay_step': index},
                        )
                        trades_executed += 1
                        run.trades_executed += 1
                    except Exception as exc:
                        errors.append(str(exc))
                        if config.get('stop_on_error', False):
                            raise

                revalue_account(account, create_snapshot=True)
                total_pnl, equity = summarize_account(account)
                ReplayStep.objects.create(
                    replay_run=run,
                    step_index=index,
                    step_timestamp=step.timestamp,
                    snapshots_used=len(step.snapshots),
                    markets_considered=len(step.snapshots),
                    proposals_generated=len(proposals),
                    trades_executed=trades_executed,
                    approvals_required=approvals_required,
                    blocked_count=blocked,
                    estimated_equity=equity,
                    notes='Step completed.' if not errors else 'Step completed with non-fatal execution errors.',
                    details={'errors': errors},
                )
                run.snapshots_considered += len(step.snapshots)
                run.markets_considered += len(step.snapshots)
                snapshot_replay_account(account, metadata={'replay_run_id': run.id, 'step_index': index})

        total_pnl, equity = summarize_account(account)
        run.total_pnl = total_pnl
        run.ending_equity = equity
        run.status = ReplayRunStatus.SUCCESS
        run.summary = (
            f'Replay completed over {len(timeline)} steps with {run.trades_executed} trades, '
            f'{run.approvals_required} approval-required decisions, and {run.blocked_count} blocked decisions.'
        )
    except Exception as exc:
        details = run.details
        details.setdefault('errors', []).append(str(exc))
        run.details = details
        run.status = ReplayRunStatus.PARTIAL if run.steps.exists() else ReplayRunStatus.FAILED
        run.summary = f'Replay terminated early: {exc}'

    run.finished_at = timezone.now()
    run.save(update_fields=[
        'status',
        'snapshots_considered',
        'markets_considered',
        'proposals_generated',
        'trades_executed',
        'approvals_required',
        'blocked_count',
        'total_pnl',
        'ending_equity',
        'summary',
        'details',
        'finished_at',
        'updated_at',
    ])
    return ReplayResult(run=run)

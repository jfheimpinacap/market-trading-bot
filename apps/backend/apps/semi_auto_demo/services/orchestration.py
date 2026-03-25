from __future__ import annotations

from dataclasses import dataclass, replace

from django.utils import timezone

from apps.markets.models import Market, MarketSourceType, MarketStatus
from apps.allocation_engine.services import AllocationConfig, evaluate_allocation
from apps.paper_trading.services.portfolio import get_active_account
from apps.operator_queue.services.escalation import ensure_queue_item_for_pending_approval
from apps.paper_trading.services.execution import execute_paper_trade
from apps.policy_engine.models import ApprovalDecisionType
from apps.proposal_engine.services import generate_trade_proposal
from apps.semi_auto_demo.models import PendingApproval, SemiAutoRun, SemiAutoRunStatus, SemiAutoRunType
from apps.semi_auto_demo.services.guards import DEFAULT_GUARD_CONFIG, evaluate_auto_execution_guards
from apps.runtime_governor.services import get_capabilities_for_current_mode, reconcile_runtime_state
from apps.safety_guard.models import SafetyEventSource
from apps.safety_guard.services.evaluation import evaluate_auto_execution


@dataclass
class RunOptions:
    market_limit: int = 8
    market_scope: str = 'mixed'
    max_auto_trades_per_run: int | None = None


def _eligible_markets(limit: int, market_scope: str):
    queryset = Market.objects.filter(is_active=True, status=MarketStatus.OPEN)
    if market_scope == 'demo_only':
        queryset = queryset.filter(source_type=MarketSourceType.DEMO)
    elif market_scope == 'real_only':
        queryset = queryset.filter(source_type=MarketSourceType.REAL_READ_ONLY)
    return queryset.order_by('-updated_at', '-id')[:limit]


def _build_run_summary(*, run: SemiAutoRun) -> str:
    return (
        f'Evaluated {run.markets_evaluated} markets, generated {run.proposals_generated} proposals, '
        f'auto-executed {run.auto_executed_count}, sent {run.approval_required_count} to manual approval, '
        f'and blocked {run.blocked_count}.'
    )


def run_evaluate_only(*, options: RunOptions | None = None) -> SemiAutoRun:
    return _run(run_type=SemiAutoRunType.EVALUATE_ONLY, execute_auto=False, options=options or RunOptions())


def run_scan_and_execute(*, options: RunOptions | None = None) -> SemiAutoRun:
    return _run(run_type=SemiAutoRunType.SCAN_AND_EXECUTE, execute_auto=True, options=options or RunOptions())


def _run(*, run_type: str, execute_auto: bool, options: RunOptions) -> SemiAutoRun:
    reconcile_runtime_state(reason='Semi-auto requested reconciliation before run.')
    runtime_caps = get_capabilities_for_current_mode()
    runtime_execute_auto = execute_auto and runtime_caps['allow_auto_execution'] and not runtime_caps['require_operator_for_all_trades']

    run = SemiAutoRun.objects.create(run_type=run_type, status=SemiAutoRunStatus.RUNNING, details={'results': []})
    results = []
    account = get_active_account()
    auto_executed = 0
    generated_proposals = []
    allocation_snapshot = {'run': None, 'proposals_selected': 0, 'allocated_total': '0.00', 'remaining_cash': str(account.cash_balance)}

    try:
        guard_config = replace(DEFAULT_GUARD_CONFIG, max_auto_trades_per_run=options.max_auto_trades_per_run) if options.max_auto_trades_per_run is not None else DEFAULT_GUARD_CONFIG

        for market in _eligible_markets(options.market_limit, options.market_scope):
            proposal = generate_trade_proposal(market=market, paper_account=account, triggered_from='automation')
            generated_proposals.append(proposal)
            run.markets_evaluated += 1
            run.proposals_generated += 1
        allocation_snapshot = evaluate_allocation(
            scope_type=options.market_scope if options.market_scope in {'real_only', 'demo_only'} else 'mixed',
            triggered_from='semi_auto_demo',
            config=AllocationConfig(
                max_candidates_considered=len(generated_proposals) or 1,
                max_executions_per_run=guard_config.max_auto_trades_per_run if guard_config.max_auto_trades_per_run is not None else 3,
            ),
            proposals=generated_proposals,
            persist=True,
        )
        allocation_map = {item['proposal'].id: item for item in allocation_snapshot['details']}

        for proposal in generated_proposals:
            market = proposal.market
            item = {
                'market_id': market.id,
                'market_title': market.title,
                'proposal_id': proposal.id,
                'policy_decision': proposal.policy_decision,
                'risk_decision': proposal.risk_decision,
                'is_actionable': proposal.is_actionable,
                'allocation_decision': allocation_map[proposal.id]['decision'],
                'allocation_quantity': str(allocation_map[proposal.id]['final_allocated_quantity']),
                'classification': 'blocked',
                'action': 'none',
                'reasons': [],
            }

            if proposal.policy_decision == ApprovalDecisionType.HARD_BLOCK:
                run.blocked_count += 1
                item['classification'] = 'blocked'
                item['reasons'].append('Policy returned HARD_BLOCK.')
            elif proposal.policy_decision == ApprovalDecisionType.APPROVAL_REQUIRED:
                if proposal.suggested_side and proposal.suggested_quantity and proposal.suggested_trade_type in {'BUY', 'SELL'}:
                    pending = PendingApproval.objects.create(
                        proposal=proposal,
                        market=proposal.market,
                        paper_account=account,
                        requested_action=proposal.suggested_trade_type,
                        suggested_side=proposal.suggested_side,
                        suggested_quantity=proposal.suggested_quantity,
                        policy_decision=proposal.policy_decision,
                        summary=proposal.headline,
                        rationale=proposal.rationale,
                        metadata={'source': 'semi_auto_demo'},
                    )
                    ensure_queue_item_for_pending_approval(pending_approval=pending)
                    run.approval_required_count += 1
                    item['classification'] = 'approval_required'
                    item['action'] = 'pending_approval_created'
                    item['pending_approval_id'] = pending.id
                else:
                    run.blocked_count += 1
                    item['classification'] = 'blocked'
                    item['reasons'].append('Policy required approval but proposal did not include executable trade fields.')
            else:
                allocated = allocation_map[proposal.id]
                if allocated['decision'] not in {'SELECTED', 'REDUCED'}:
                    run.blocked_count += 1
                    item['classification'] = 'blocked'
                    item['reasons'] = allocated['rationale']
                    results.append(item)
                    continue
                passed, reasons = evaluate_auto_execution_guards(proposal=proposal, auto_trades_so_far=auto_executed, config=guard_config)
                item['classification'] = 'auto_executable' if passed else 'blocked'
                item['reasons'] = reasons

                safety_decision = evaluate_auto_execution(
                    proposal=proposal,
                    auto_trades_so_far=auto_executed,
                    source=SafetyEventSource.SEMI_AUTO,
                )

                if runtime_execute_auto and passed and safety_decision.allowed:
                    execution = execute_paper_trade(
                        market=proposal.market,
                        trade_type=proposal.suggested_trade_type,
                        side=proposal.suggested_side,
                        quantity=allocated['final_allocated_quantity'],
                        account=account,
                        notes='Semi-auto demo auto execution.',
                        metadata={
                            'semi_auto_proposal_id': proposal.id,
                            'semi_auto_run_id': run.id,
                            'semi_auto_execution_origin': 'auto',
                            'allocation_run_id': allocation_snapshot['run'].id if allocation_snapshot.get('run') else None,
                        },
                    )
                    proposal.proposal_status = 'EXECUTED'
                    proposal.save(update_fields=['proposal_status', 'updated_at'])
                    auto_executed += 1
                    run.auto_executed_count += 1
                    item['action'] = 'auto_executed'
                    item['trade_id'] = execution.trade.id
                elif runtime_execute_auto and passed and safety_decision.requires_manual_approval:
                    pending = PendingApproval.objects.create(
                        proposal=proposal,
                        market=proposal.market,
                        paper_account=account,
                        requested_action=proposal.suggested_trade_type,
                        suggested_side=proposal.suggested_side,
                        suggested_quantity=proposal.suggested_quantity,
                        policy_decision='APPROVAL_REQUIRED',
                        summary=f'Safety escalation: {proposal.headline}',
                        rationale='; '.join(safety_decision.reasons),
                        metadata={'source': 'safety_guard', 'classification': safety_decision.classification},
                    )
                    ensure_queue_item_for_pending_approval(pending_approval=pending)
                    run.approval_required_count += 1
                    item['classification'] = 'approval_required'
                    item['action'] = 'pending_approval_created'
                    item['pending_approval_id'] = pending.id
                    item['reasons'] = item.get('reasons', []) + safety_decision.reasons
                elif not runtime_execute_auto and passed and safety_decision.allowed:
                    item['action'] = 'eligible_for_auto_execution'
                else:
                    run.blocked_count += 1
                    item['reasons'] = item.get('reasons', []) + safety_decision.reasons

            results.append(item)

        run.status = SemiAutoRunStatus.SUCCESS
    except Exception as exc:
        run.status = SemiAutoRunStatus.PARTIAL if run.markets_evaluated else SemiAutoRunStatus.FAILED
        results.append({'error': str(exc)})

    run.finished_at = timezone.now()
    run.details = {
        'results': results,
        'runtime': {
            'mode': runtime_caps['mode'],
            'allow_auto_execution': runtime_caps['allow_auto_execution'],
            'require_operator_for_all_trades': runtime_caps['require_operator_for_all_trades'],
            'blocked_reasons': runtime_caps['blocked_reasons'],
        },
        'allocation': {
            'run_id': allocation_snapshot['run'].id if allocation_snapshot.get('run') else None,
            'proposals_selected': allocation_snapshot['proposals_selected'],
            'allocated_total': str(allocation_snapshot['allocated_total']),
            'remaining_cash': str(allocation_snapshot['remaining_cash']),
        },
        'guardrails': {
            'max_auto_quantity': str(guard_config.max_auto_quantity),
            'max_auto_trades_per_run': guard_config.max_auto_trades_per_run,
            'max_market_exposure_value': str(guard_config.max_market_exposure_value),
            'max_total_exposure_value': str(guard_config.max_total_exposure_value),
            'market_scope': options.market_scope,
            'buy_only_auto_execution': True,
        },
    }
    run.summary = _build_run_summary(run=run)
    run.save()
    return run

from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.markets.models import Market, MarketStatus
from apps.paper_trading.services.portfolio import get_active_account
from apps.paper_trading.services.execution import execute_paper_trade
from apps.policy_engine.models import ApprovalDecisionType
from apps.proposal_engine.services import generate_trade_proposal
from apps.semi_auto_demo.models import PendingApproval, SemiAutoRun, SemiAutoRunStatus, SemiAutoRunType
from apps.semi_auto_demo.services.guards import DEFAULT_GUARD_CONFIG, evaluate_auto_execution_guards


@dataclass
class RunOptions:
    market_limit: int = 8


def _eligible_markets(limit: int):
    return Market.objects.filter(is_active=True, status=MarketStatus.OPEN).order_by('-updated_at', '-id')[:limit]


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
    run = SemiAutoRun.objects.create(run_type=run_type, status=SemiAutoRunStatus.RUNNING, details={'results': []})
    results = []
    account = get_active_account()
    auto_executed = 0

    try:
        for market in _eligible_markets(options.market_limit):
            proposal = generate_trade_proposal(market=market, paper_account=account, triggered_from='automation')
            run.markets_evaluated += 1
            run.proposals_generated += 1

            item = {
                'market_id': market.id,
                'market_title': market.title,
                'proposal_id': proposal.id,
                'policy_decision': proposal.policy_decision,
                'risk_decision': proposal.risk_decision,
                'is_actionable': proposal.is_actionable,
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
                    run.approval_required_count += 1
                    item['classification'] = 'approval_required'
                    item['action'] = 'pending_approval_created'
                    item['pending_approval_id'] = pending.id
                else:
                    run.blocked_count += 1
                    item['classification'] = 'blocked'
                    item['reasons'].append('Policy required approval but proposal did not include executable trade fields.')
            else:
                passed, reasons = evaluate_auto_execution_guards(proposal=proposal, auto_trades_so_far=auto_executed, config=DEFAULT_GUARD_CONFIG)
                item['classification'] = 'auto_executable' if passed else 'blocked'
                item['reasons'] = reasons

                if execute_auto and passed:
                    execution = execute_paper_trade(
                        market=proposal.market,
                        trade_type=proposal.suggested_trade_type,
                        side=proposal.suggested_side,
                        quantity=proposal.suggested_quantity,
                        account=account,
                        notes='Semi-auto demo auto execution.',
                        metadata={'semi_auto_proposal_id': proposal.id, 'semi_auto_run_id': run.id, 'semi_auto_execution_origin': 'auto'},
                    )
                    proposal.proposal_status = 'EXECUTED'
                    proposal.save(update_fields=['proposal_status', 'updated_at'])
                    auto_executed += 1
                    run.auto_executed_count += 1
                    item['action'] = 'auto_executed'
                    item['trade_id'] = execution.trade.id
                elif not execute_auto and passed:
                    item['action'] = 'eligible_for_auto_execution'
                else:
                    run.blocked_count += 1

            results.append(item)

        run.status = SemiAutoRunStatus.SUCCESS
    except Exception as exc:
        run.status = SemiAutoRunStatus.PARTIAL if run.markets_evaluated else SemiAutoRunStatus.FAILED
        results.append({'error': str(exc)})

    run.finished_at = timezone.now()
    run.details = {
        'results': results,
        'guardrails': {
            'max_auto_quantity': str(DEFAULT_GUARD_CONFIG.max_auto_quantity),
            'max_auto_trades_per_run': DEFAULT_GUARD_CONFIG.max_auto_trades_per_run,
            'max_market_exposure_value': str(DEFAULT_GUARD_CONFIG.max_market_exposure_value),
            'max_total_exposure_value': str(DEFAULT_GUARD_CONFIG.max_total_exposure_value),
            'buy_only_auto_execution': True,
        },
    }
    run.summary = _build_run_summary(run=run)
    run.save()
    return run

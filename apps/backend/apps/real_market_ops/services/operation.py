from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import get_active_account
from apps.policy_engine.models import ApprovalDecisionType
from apps.proposal_engine.services import generate_trade_proposal
from apps.real_market_ops.models import RealMarketOperationRun, RealMarketRunStatus
from apps.real_market_ops.services.eligibility import evaluate_real_market_eligibility
from apps.real_market_ops.services.real_scope import get_real_scope_config
from apps.semi_auto_demo.models import PendingApproval
from apps.semi_auto_demo.services.guards import DEFAULT_GUARD_CONFIG, evaluate_auto_execution_guards
from apps.safety_guard.models import SafetyEventSource
from apps.safety_guard.services import get_safety_status
from apps.safety_guard.services.evaluation import evaluate_auto_execution


@dataclass
class RunOptions:
    execute_auto: bool = False
    triggered_from: str = 'manual'


def _to_json_safe(value):
    if isinstance(value, dict):
        return {key: _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_json_safe(item) for item in value]
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


def _build_summary(run: RealMarketOperationRun) -> str:
    return (
        f'Real scope run {run.status}: considered={run.markets_considered}, eligible={run.markets_eligible}, '
        f'proposals={run.proposals_generated}, auto={run.auto_executed_count}, approvals={run.approval_required_count}, blocked={run.blocked_count}.'
    )


def run_real_market_operation(*, options: RunOptions) -> RealMarketOperationRun:
    snapshot = evaluate_real_market_eligibility()
    scope_config = get_real_scope_config()

    run = RealMarketOperationRun.objects.create(
        status=RealMarketRunStatus.SKIPPED,
        triggered_from=options.triggered_from,
        started_at=timezone.now(),
        providers_considered=len(snapshot.providers_considered),
        markets_considered=len(snapshot.considered),
        markets_eligible=len(snapshot.eligible),
        skipped_stale_count=snapshot.counters['skipped_stale_count'],
        skipped_degraded_provider_count=snapshot.counters['skipped_degraded_provider_count'],
        skipped_no_pricing_count=snapshot.counters['skipped_no_pricing_count'],
        details={
            'scope': snapshot.scope,
            'provider_status': _to_json_safe(snapshot.provider_status),
            'excluded_markets': snapshot.excluded[:40],
            'evaluation_only': not options.execute_auto,
            'execution_mode': 'paper_demo_only',
            'source_type_required': 'real_read_only',
            'results': [],
        },
    )

    if not scope_config.enabled:
        run.summary = 'Real market ops scope is disabled by configuration.'
        run.finished_at = timezone.now()
        run.save(update_fields=['summary', 'finished_at', 'updated_at'])
        return run

    safety = get_safety_status()
    if options.execute_auto and (safety['kill_switch_enabled'] or safety['hard_stop_active']):
        run.summary = 'Real market ops blocked by safety kill switch/hard stop.'
        run.status = RealMarketRunStatus.SKIPPED
        run.finished_at = timezone.now()
        run.details = {**run.details, 'safety_block': _to_json_safe(safety)}
        run.save(update_fields=['status', 'summary', 'finished_at', 'details', 'updated_at'])
        return run

    account = get_active_account()
    auto_trades = 0
    results: list[dict] = []

    for market in snapshot.eligible:
        try:
            proposal = generate_trade_proposal(market=market, paper_account=account, triggered_from='real_market_ops')
            run.proposals_generated += 1
            item = {
                'market_id': market.id,
                'market_title': market.title,
                'provider': market.provider.slug,
                'source_type': market.source_type,
                'proposal_id': proposal.id,
                'policy_decision': proposal.policy_decision,
                'risk_decision': proposal.risk_decision,
                'action': 'none',
                'classification': 'blocked',
                'reasons': [],
            }

            trade_ready = proposal.suggested_side and proposal.suggested_quantity and proposal.suggested_trade_type in {'BUY', 'SELL'}

            if proposal.policy_decision == ApprovalDecisionType.HARD_BLOCK:
                run.blocked_count += 1
                item['reasons'].append('policy_hard_block')
            elif proposal.policy_decision == ApprovalDecisionType.APPROVAL_REQUIRED:
                if trade_ready:
                    PendingApproval.objects.create(
                        proposal=proposal,
                        market=proposal.market,
                        paper_account=account,
                        requested_action=proposal.suggested_trade_type,
                        suggested_side=proposal.suggested_side,
                        suggested_quantity=proposal.suggested_quantity,
                        policy_decision=proposal.policy_decision,
                        summary=f'Real market scope approval required: {proposal.headline}',
                        rationale=proposal.rationale,
                        metadata={'source': 'real_market_ops', 'source_type': 'real_read_only'},
                    )
                    run.approval_required_count += 1
                    item['classification'] = 'approval_required'
                    item['action'] = 'pending_approval_created'
                else:
                    run.blocked_count += 1
                    item['reasons'].append('approval_required_missing_trade_fields')
            else:
                passed, reasons = evaluate_auto_execution_guards(proposal=proposal, auto_trades_so_far=auto_trades, config=DEFAULT_GUARD_CONFIG)
                safety_decision = evaluate_auto_execution(proposal=proposal, auto_trades_so_far=auto_trades, source=SafetyEventSource.SEMI_AUTO)

                if options.execute_auto and passed and safety_decision.allowed and auto_trades < scope_config.max_real_auto_trades_per_cycle and trade_ready:
                    execution = execute_paper_trade(
                        market=proposal.market,
                        trade_type=proposal.suggested_trade_type,
                        side=proposal.suggested_side,
                        quantity=proposal.suggested_quantity,
                        account=account,
                        notes='Autonomous real-market scope paper execution.',
                        metadata={
                            'real_market_ops_run_id': run.id,
                            'execution_mode': 'paper_demo_only',
                            'source_type': 'real_read_only',
                        },
                    )
                    run.auto_executed_count += 1
                    auto_trades += 1
                    item['classification'] = 'auto_executed'
                    item['action'] = 'paper_trade_executed'
                    item['trade_id'] = execution.trade.id
                elif options.execute_auto and passed and safety_decision.requires_manual_approval and trade_ready:
                    PendingApproval.objects.create(
                        proposal=proposal,
                        market=proposal.market,
                        paper_account=account,
                        requested_action=proposal.suggested_trade_type,
                        suggested_side=proposal.suggested_side,
                        suggested_quantity=proposal.suggested_quantity,
                        policy_decision='APPROVAL_REQUIRED',
                        summary=f'Real market safety escalation: {proposal.headline}',
                        rationale='; '.join(safety_decision.reasons),
                        metadata={'source': 'real_market_ops', 'classification': safety_decision.classification},
                    )
                    run.approval_required_count += 1
                    item['classification'] = 'approval_required'
                    item['action'] = 'pending_approval_created'
                elif options.execute_auto and passed and auto_trades >= scope_config.max_real_auto_trades_per_cycle:
                    run.blocked_count += 1
                    item['reasons'] = ['max_real_auto_trades_reached']
                elif options.execute_auto and passed and not trade_ready:
                    run.blocked_count += 1
                    item['reasons'] = ['proposal_missing_trade_fields']
                elif passed:
                    item['classification'] = 'eligible_for_auto_execution'
                    item['action'] = 'evaluate_only'
                else:
                    run.blocked_count += 1
                    item['reasons'] = reasons + safety_decision.reasons

            results.append(item)
        except Exception as market_exc:
            run.blocked_count += 1
            results.append(
                {
                    'market_id': market.id,
                    'market_title': market.title,
                    'provider': market.provider.slug,
                    'classification': 'blocked',
                    'action': 'none',
                    'reasons': ['proposal_generation_failed'],
                    'error': str(market_exc),
                }
            )

    run.details = {**run.details, 'results': results}
    if run.proposals_generated == 0 and run.markets_eligible == 0:
        run.status = RealMarketRunStatus.SKIPPED
    elif run.proposals_generated == 0:
        run.status = RealMarketRunStatus.PARTIAL
    elif run.blocked_count > 0 and run.auto_executed_count == 0 and run.approval_required_count == 0:
        run.status = RealMarketRunStatus.PARTIAL
    else:
        run.status = RealMarketRunStatus.SUCCESS

    run.finished_at = timezone.now()
    run.summary = _build_summary(run)
    run.save()
    return run

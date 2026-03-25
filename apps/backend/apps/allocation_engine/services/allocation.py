from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN

from django.utils import timezone

from apps.allocation_engine.models import AllocationDecision, AllocationDecisionType, AllocationRun, AllocationRunStatus, AllocationScopeType
from apps.allocation_engine.services.portfolio_context import build_portfolio_context
from apps.allocation_engine.services.ranking import rank_proposals
from apps.markets.models import MarketSourceType
from apps.paper_trading.services.portfolio import get_active_account
from apps.policy_engine.models import ApprovalDecisionType
from apps.proposal_engine.models import ProposalStatus, TradeProposal


@dataclass
class AllocationConfig:
    max_candidates_considered: int = 20
    max_executions_per_run: int = 3
    max_total_allocation_per_run: Decimal = Decimal('1200.00')
    max_allocation_per_market: Decimal = Decimal('400.00')
    reserve_cash_amount: Decimal = Decimal('250.00')
    prefer_real_markets: bool = False
    penalize_existing_exposure: bool = True
    penalize_degraded_provider: bool = True
    penalize_unfavorable_learning: bool = True



def _build_summary(*, considered: int, selected: int, rejected: int, allocated_total: Decimal, remaining_cash: Decimal) -> str:
    return (
        f'Allocation evaluated {considered} proposals, selected {selected}, rejected {rejected}, '
        f'allocated {allocated_total:.2f}, remaining_cash {remaining_cash:.2f}.'
    )


def _select_candidates(*, scope_type: str, max_candidates: int) -> list[TradeProposal]:
    queryset = TradeProposal.objects.select_related('market', 'market__provider').filter(
        proposal_status=ProposalStatus.ACTIVE,
        is_actionable=True,
        suggested_quantity__isnull=False,
        suggested_side__isnull=False,
    )
    if scope_type == AllocationScopeType.REAL_ONLY:
        queryset = queryset.filter(market__source_type=MarketSourceType.REAL_READ_ONLY)
    elif scope_type == AllocationScopeType.DEMO_ONLY:
        queryset = queryset.filter(market__source_type=MarketSourceType.DEMO)

    return list(queryset.order_by('-created_at', '-id')[:max_candidates])


def evaluate_allocation(*, scope_type: str = AllocationScopeType.MIXED, triggered_from: str = 'manual', config: AllocationConfig | None = None, proposals: list[TradeProposal] | None = None, persist: bool = False) -> dict:
    cfg = config or AllocationConfig()
    account = get_active_account()
    portfolio = build_portfolio_context(account=account, reserve_cash_amount=cfg.reserve_cash_amount)

    candidates = proposals if proposals is not None else _select_candidates(scope_type=scope_type, max_candidates=cfg.max_candidates_considered)
    ranked = rank_proposals(
        proposals=candidates,
        prefer_real_markets=cfg.prefer_real_markets,
        penalize_existing_exposure=cfg.penalize_existing_exposure,
        exposure_by_market=portfolio.market_exposure,
        penalize_degraded_provider=cfg.penalize_degraded_provider,
        penalize_unfavorable_learning=cfg.penalize_unfavorable_learning,
    )

    run_limit = min(portfolio.available_cash, cfg.max_total_allocation_per_run)
    remaining_budget = run_limit
    selected_count = 0
    rejected_count = 0
    allocated_total = Decimal('0.00')
    market_allocated: dict[int, Decimal] = {}
    decisions: list[dict] = []

    for idx, item in enumerate(ranked, start=1):
        proposal = item.proposal
        rationale = list(item.penalties)
        requested_qty = proposal.suggested_quantity or Decimal('0.0000')
        if requested_qty <= Decimal('0.0000'):
            decisions.append({'proposal': proposal, 'rank': idx, 'decision': AllocationDecisionType.REJECTED, 'final_allocated_quantity': Decimal('0.0000'), 'rationale': rationale + ['invalid_quantity'], 'rank_score': item.rank_score})
            rejected_count += 1
            continue

        if proposal.policy_decision == ApprovalDecisionType.HARD_BLOCK:
            decisions.append({'proposal': proposal, 'rank': idx, 'decision': AllocationDecisionType.REJECTED, 'final_allocated_quantity': Decimal('0.0000'), 'rationale': rationale + ['hard_block_excluded'], 'rank_score': item.rank_score})
            rejected_count += 1
            continue

        if proposal.policy_decision == ApprovalDecisionType.APPROVAL_REQUIRED:
            decisions.append({'proposal': proposal, 'rank': idx, 'decision': AllocationDecisionType.SKIPPED, 'final_allocated_quantity': Decimal('0.0000'), 'rationale': rationale + ['queued_for_manual_approval'], 'rank_score': item.rank_score})
            continue

        if selected_count >= cfg.max_executions_per_run:
            decisions.append({'proposal': proposal, 'rank': idx, 'decision': AllocationDecisionType.SKIPPED, 'final_allocated_quantity': Decimal('0.0000'), 'rationale': rationale + ['max_executions_reached'], 'rank_score': item.rank_score})
            continue

        if remaining_budget <= Decimal('0.00'):
            decisions.append({'proposal': proposal, 'rank': idx, 'decision': AllocationDecisionType.SKIPPED, 'final_allocated_quantity': Decimal('0.0000'), 'rationale': rationale + ['run_budget_exhausted'], 'rank_score': item.rank_score})
            continue

        reference_price = proposal.suggested_price_reference or proposal.market.current_yes_price or proposal.market.current_no_price or Decimal('1.00')
        requested_value = (requested_qty * reference_price).quantize(Decimal('0.01'))
        existing_market_exposure = portfolio.market_exposure.get(proposal.market_id, Decimal('0.00'))
        already_allocated_market = market_allocated.get(proposal.market_id, Decimal('0.00'))
        market_remaining_cap = cfg.max_allocation_per_market - existing_market_exposure - already_allocated_market

        if market_remaining_cap <= Decimal('0.00'):
            decisions.append({'proposal': proposal, 'rank': idx, 'decision': AllocationDecisionType.REJECTED, 'final_allocated_quantity': Decimal('0.0000'), 'rationale': rationale + ['market_exposure_cap_reached'], 'rank_score': item.rank_score})
            rejected_count += 1
            continue

        allocatable_value = min(requested_value, market_remaining_cap, remaining_budget)
        if allocatable_value <= Decimal('0.00'):
            decisions.append({'proposal': proposal, 'rank': idx, 'decision': AllocationDecisionType.SKIPPED, 'final_allocated_quantity': Decimal('0.0000'), 'rationale': rationale + ['no_allocatable_budget'], 'rank_score': item.rank_score})
            continue

        final_qty = (allocatable_value / reference_price).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
        if final_qty <= Decimal('0.0000'):
            decisions.append({'proposal': proposal, 'rank': idx, 'decision': AllocationDecisionType.SKIPPED, 'final_allocated_quantity': Decimal('0.0000'), 'rationale': rationale + ['allocation_too_small'], 'rank_score': item.rank_score})
            continue

        final_value = (final_qty * reference_price).quantize(Decimal('0.01'))
        remaining_budget -= final_value
        allocated_total += final_value
        market_allocated[proposal.market_id] = already_allocated_market + final_value
        selected_count += 1
        decisions.append(
            {
                'proposal': proposal,
                'rank': idx,
                'decision': AllocationDecisionType.SELECTED if final_qty == requested_qty else AllocationDecisionType.REDUCED,
                'final_allocated_quantity': final_qty,
                'rationale': rationale,
                'rank_score': item.rank_score,
                'requested_quantity': requested_qty,
                'reference_price': reference_price,
                'allocated_value': final_value,
            }
        )

    remaining_cash = portfolio.available_cash - allocated_total
    summary = _build_summary(
        considered=len(candidates),
        selected=selected_count,
        rejected=rejected_count,
        allocated_total=allocated_total,
        remaining_cash=remaining_cash,
    )

    run_obj = None
    if persist:
        run_obj = AllocationRun.objects.create(
            status=AllocationRunStatus.SUCCESS,
            scope_type=scope_type,
            triggered_from=triggered_from,
            started_at=timezone.now(),
            finished_at=timezone.now(),
            proposals_considered=len(candidates),
            proposals_ranked=len(ranked),
            proposals_selected=selected_count,
            proposals_rejected=rejected_count,
            allocated_total=allocated_total,
            remaining_cash=remaining_cash,
            summary=summary,
            details={
                'config': {
                    'max_candidates_considered': cfg.max_candidates_considered,
                    'max_executions_per_run': cfg.max_executions_per_run,
                    'max_total_allocation_per_run': str(cfg.max_total_allocation_per_run),
                    'max_allocation_per_market': str(cfg.max_allocation_per_market),
                    'reserve_cash_amount': str(cfg.reserve_cash_amount),
                    'prefer_real_markets': cfg.prefer_real_markets,
                    'penalize_existing_exposure': cfg.penalize_existing_exposure,
                    'penalize_degraded_provider': cfg.penalize_degraded_provider,
                    'penalize_unfavorable_learning': cfg.penalize_unfavorable_learning,
                }
            },
        )
        AllocationDecision.objects.bulk_create(
            [
                AllocationDecision(
                    run=run_obj,
                    proposal=entry['proposal'],
                    rank=entry['rank'],
                    final_allocated_quantity=entry['final_allocated_quantity'],
                    decision=entry['decision'],
                    rationale='; '.join(entry['rationale']),
                    details={
                        'rank_score': str(entry.get('rank_score', '0')),
                        'requested_quantity': str(entry.get('requested_quantity', '0.0000')),
                        'reference_price': str(entry.get('reference_price', '0')),
                        'allocated_value': str(entry.get('allocated_value', '0.00')),
                    },
                )
                for entry in decisions
            ]
        )

    return {
        'run': run_obj,
        'scope_type': scope_type,
        'triggered_from': triggered_from,
        'proposals_considered': len(candidates),
        'proposals_ranked': len(ranked),
        'proposals_selected': selected_count,
        'proposals_rejected': rejected_count,
        'allocated_total': allocated_total,
        'remaining_cash': remaining_cash,
        'summary': summary,
        'details': decisions,
    }

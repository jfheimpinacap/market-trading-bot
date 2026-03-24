from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.paper_trading.models import PaperPositionStatus
from apps.paper_trading.services.market_pricing import get_paper_tradability
from apps.paper_trading.services.valuation import get_market_price
from apps.proposal_engine.models import ProposalTradeType, TradeProposal


@dataclass(frozen=True)
class GuardConfig:
    max_auto_quantity: Decimal = Decimal('3.0000')
    max_auto_trades_per_run: int = 2
    max_market_exposure_value: Decimal = Decimal('750.00')
    max_total_exposure_value: Decimal = Decimal('3000.00')


DEFAULT_GUARD_CONFIG = GuardConfig()


def evaluate_auto_execution_guards(*, proposal: TradeProposal, auto_trades_so_far: int, config: GuardConfig = DEFAULT_GUARD_CONFIG) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    account = proposal.paper_account
    market = proposal.market

    if proposal.suggested_trade_type != ProposalTradeType.BUY:
        reasons.append('Only BUY proposals can auto-execute in semi-auto mode.')

    if not proposal.is_actionable:
        reasons.append('Proposal is not actionable.')

    if proposal.suggested_quantity is None or proposal.suggested_quantity <= Decimal('0.0000'):
        reasons.append('Suggested quantity is missing or invalid.')
    elif proposal.suggested_quantity > config.max_auto_quantity:
        reasons.append(f'Suggested quantity exceeds max auto quantity {config.max_auto_quantity}.')

    tradability = get_paper_tradability(market)
    if not tradability.is_tradable:
        reasons.append(tradability.message)

    if auto_trades_so_far >= config.max_auto_trades_per_run:
        reasons.append(f'Max auto trades per run ({config.max_auto_trades_per_run}) reached.')

    if account is None:
        reasons.append('No active paper account linked to proposal.')
        return False, reasons

    if proposal.suggested_side is None:
        reasons.append('Suggested side is required for auto execution.')
        return False, reasons

    estimated_price = get_market_price(market=market, side=proposal.suggested_side)
    estimated_cost = (proposal.suggested_quantity or Decimal('0.0000')) * estimated_price
    if account.cash_balance < estimated_cost:
        reasons.append('Insufficient paper account cash for estimated execution cost.')

    open_positions = account.positions.filter(status=PaperPositionStatus.OPEN, quantity__gt=0)
    market_exposure = sum((position.market_value for position in open_positions.filter(market=market)), Decimal('0.00'))
    total_exposure = sum((position.market_value for position in open_positions), Decimal('0.00'))

    if market_exposure + estimated_cost > config.max_market_exposure_value:
        reasons.append(f'Estimated exposure exceeds per-market limit {config.max_market_exposure_value}.')
    if total_exposure + estimated_cost > config.max_total_exposure_value:
        reasons.append(f'Estimated exposure exceeds total limit {config.max_total_exposure_value}.')

    return len(reasons) == 0, reasons

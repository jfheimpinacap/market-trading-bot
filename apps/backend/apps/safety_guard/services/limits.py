from __future__ import annotations

from decimal import Decimal

from apps.paper_trading.models import PaperPositionStatus
from apps.paper_trading.services.market_pricing import get_paper_tradability
from apps.paper_trading.services.valuation import get_market_price
from apps.proposal_engine.models import TradeProposal
from apps.safety_guard.models import SafetyPolicyConfig


def get_exposure_snapshot(*, proposal: TradeProposal) -> dict:
    account = proposal.paper_account
    market = proposal.market
    quantity = proposal.suggested_quantity or Decimal('0.0000')

    if account is None or proposal.suggested_side is None:
        return {
            'estimated_cost': Decimal('0.00'),
            'market_exposure': Decimal('0.00'),
            'total_exposure': Decimal('0.00'),
            'projected_market_exposure': Decimal('0.00'),
            'projected_total_exposure': Decimal('0.00'),
            'price': Decimal('0.00'),
        }

    price = get_market_price(market=market, side=proposal.suggested_side)
    estimated_cost = quantity * price

    open_positions = account.positions.filter(status=PaperPositionStatus.OPEN, quantity__gt=0)
    market_exposure = sum((position.market_value for position in open_positions.filter(market=market)), Decimal('0.00'))
    total_exposure = sum((position.market_value for position in open_positions), Decimal('0.00'))

    return {
        'estimated_cost': estimated_cost,
        'market_exposure': market_exposure,
        'total_exposure': total_exposure,
        'projected_market_exposure': market_exposure + estimated_cost,
        'projected_total_exposure': total_exposure + estimated_cost,
        'price': price,
    }


def evaluate_exposure_limits(*, proposal: TradeProposal, config: SafetyPolicyConfig) -> tuple[bool, list[str], dict]:
    reasons: list[str] = []
    snapshot = get_exposure_snapshot(proposal=proposal)

    if proposal.paper_account is None:
        reasons.append('No active paper account for safety exposure checks.')
        return False, reasons, snapshot

    tradability = get_paper_tradability(proposal.market)
    if not tradability.is_tradable:
        reasons.append(tradability.message)

    if snapshot['projected_market_exposure'] > config.max_position_value_per_market:
        reasons.append(f'Per-market exposure limit hit ({config.max_position_value_per_market}).')

    if snapshot['projected_total_exposure'] > config.max_total_open_exposure:
        reasons.append(f'Total exposure limit hit ({config.max_total_open_exposure}).')

    return len(reasons) == 0, reasons, snapshot


def evaluate_loss_limits(*, config: SafetyPolicyConfig, equity: Decimal, initial_balance: Decimal, unrealized_pnl: Decimal) -> tuple[bool, list[str], dict]:
    drawdown = initial_balance - equity
    unrealized_loss = abs(unrealized_pnl) if unrealized_pnl < 0 else Decimal('0.00')

    reasons = []
    if drawdown > config.max_daily_or_session_drawdown:
        reasons.append(f'Drawdown limit exceeded ({config.max_daily_or_session_drawdown}).')
    if unrealized_loss > config.max_unrealized_loss_threshold:
        reasons.append(f'Unrealized loss threshold exceeded ({config.max_unrealized_loss_threshold}).')

    return len(reasons) == 0, reasons, {
        'drawdown': drawdown,
        'unrealized_loss': unrealized_loss,
    }

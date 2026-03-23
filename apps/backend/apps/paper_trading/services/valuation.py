from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from apps.markets.models import Market, MarketStatus
from apps.paper_trading.models import (
    PaperAccount,
    PaperPosition,
    PaperPositionSide,
    PaperPositionStatus,
)

FOUR_DP = Decimal('0.0001')
TWO_DP = Decimal('0.01')
ZERO = Decimal('0')


class PaperTradingError(Exception):
    """Base domain error for paper trading services."""


class PaperTradingValidationError(PaperTradingError):
    """Raised when a paper trade request is not valid."""


class PaperTradingRejectionError(PaperTradingError):
    """Raised when a paper trade cannot be executed in demo mode."""


def quantize_price(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(str(value or '0')).quantize(FOUR_DP, rounding=ROUND_HALF_UP)


def quantize_money(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(str(value or '0')).quantize(TWO_DP, rounding=ROUND_HALF_UP)


def quantize_quantity(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(str(value or '0')).quantize(FOUR_DP, rounding=ROUND_HALF_UP)


def get_market_price(*, market: Market, side: str) -> Decimal:
    if side == PaperPositionSide.YES:
        if market.current_yes_price is not None:
            return quantize_price(market.current_yes_price)
        probability = Decimal(str(market.current_market_probability or '0'))
        return quantize_price(probability * Decimal('100'))

    if market.current_no_price is not None:
        return quantize_price(market.current_no_price)

    probability = Decimal(str(market.current_market_probability or '0'))
    return quantize_price((Decimal('1') - probability) * Decimal('100'))


def validate_market_for_trading(market: Market) -> None:
    if market.status != MarketStatus.OPEN or not market.is_active:
        raise PaperTradingValidationError(
            f'Market {market.id} is not available for paper trading in status {market.status}.',
        )


@transaction.atomic
def revalue_position(position: PaperPosition, *, save: bool = True) -> PaperPosition:
    mark_price = get_market_price(market=position.market, side=position.side)
    quantity = quantize_quantity(position.quantity)
    cost_basis = quantize_money(quantity * Decimal(str(position.average_entry_price or '0')))
    market_value = quantize_money(quantity * mark_price)
    unrealized_pnl = quantize_money(market_value - cost_basis)

    position.current_mark_price = mark_price
    position.cost_basis = cost_basis
    position.market_value = market_value
    position.unrealized_pnl = unrealized_pnl
    position.status = PaperPositionStatus.OPEN if quantity > ZERO else PaperPositionStatus.CLOSED
    position.last_marked_at = timezone.now()
    if position.status == PaperPositionStatus.CLOSED and position.closed_at is None:
        position.closed_at = position.last_marked_at
    if position.status == PaperPositionStatus.OPEN:
        position.closed_at = None

    if save:
        position.save(update_fields=[
            'current_mark_price',
            'cost_basis',
            'market_value',
            'unrealized_pnl',
            'status',
            'last_marked_at',
            'closed_at',
            'updated_at',
        ])
    return position


@transaction.atomic
def revalue_account(account: PaperAccount, *, create_snapshot: bool = False) -> PaperAccount:
    positions = list(account.positions.select_related('market').all())
    open_positions = 0
    total_market_value = ZERO
    realized_total = ZERO
    unrealized_total = ZERO

    for position in positions:
        revalue_position(position)
        realized_total += Decimal(str(position.realized_pnl or '0'))
        unrealized_total += Decimal(str(position.unrealized_pnl or '0'))
        total_market_value += Decimal(str(position.market_value or '0'))
        if position.status == PaperPositionStatus.OPEN and Decimal(str(position.quantity or '0')) > ZERO:
            open_positions += 1

    account.realized_pnl = quantize_money(realized_total)
    account.unrealized_pnl = quantize_money(unrealized_total)
    account.total_pnl = quantize_money(account.realized_pnl + account.unrealized_pnl)
    account.equity = quantize_money(Decimal(str(account.cash_balance or '0')) + total_market_value)
    account.save(update_fields=['realized_pnl', 'unrealized_pnl', 'total_pnl', 'equity', 'updated_at'])

    if create_snapshot:
        from apps.paper_trading.services.portfolio import create_portfolio_snapshot

        create_portfolio_snapshot(account=account, open_positions_count=open_positions)

    return account

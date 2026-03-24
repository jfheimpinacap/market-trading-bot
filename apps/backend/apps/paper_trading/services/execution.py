from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.markets.models import Market
from apps.paper_trading.models import (
    PaperAccount,
    PaperPosition,
    PaperPositionSide,
    PaperPositionStatus,
    PaperTrade,
    PaperTradeStatus,
    PaperTradeType,
)
from apps.paper_trading.services.portfolio import create_portfolio_snapshot, get_active_account
from apps.paper_trading.services.market_pricing import resolve_market_price
from apps.paper_trading.services.valuation import (
    PaperTradingRejectionError,
    PaperTradingValidationError,
    get_market_price,
    quantize_money,
    quantize_quantity,
    revalue_account,
    revalue_position,
    validate_market_for_trading,
)

ZERO = Decimal('0')


@dataclass
class ExecutionResult:
    account: PaperAccount
    position: PaperPosition
    trade: PaperTrade


@transaction.atomic
def execute_paper_trade(*, market: Market, trade_type: str, side: str, quantity, account: PaperAccount | None = None, notes: str = '', metadata: dict | None = None) -> ExecutionResult:
    if account is None:
        account = get_active_account()

    trade_type = trade_type.upper()
    side = side.upper()
    metadata = metadata or {}
    quantity = quantize_quantity(quantity)

    if trade_type not in PaperTradeType.values:
        raise PaperTradingValidationError(f'Unsupported trade_type: {trade_type}')
    if side not in PaperPositionSide.values:
        raise PaperTradingValidationError(f'Unsupported side: {side}')
    if quantity <= ZERO:
        raise PaperTradingValidationError('Quantity must be greater than zero.')

    validate_market_for_trading(market)
    price_resolution = resolve_market_price(market=market, side=side)
    price = get_market_price(market=market, side=side)
    gross_amount = quantize_money(quantity * price)
    fees = quantize_money(Decimal('0'))

    position, _ = PaperPosition.objects.select_for_update().get_or_create(
        account=account,
        market=market,
        side=side,
        defaults={
            'opened_at': timezone.now(),
            'status': PaperPositionStatus.OPEN,
            'metadata': {},
        },
    )

    if trade_type == PaperTradeType.BUY:
        total_cost = quantize_money(gross_amount + fees)
        if account.cash_balance < total_cost:
            raise PaperTradingRejectionError('Insufficient paper cash balance to execute buy trade.')

        existing_cost = quantize_money(position.quantity * position.average_entry_price)
        new_quantity = quantize_quantity(position.quantity + quantity)
        new_cost_basis = quantize_money(existing_cost + gross_amount)
        average_entry_price = Decimal('0.0000') if new_quantity <= ZERO else (new_cost_basis / new_quantity)

        account.cash_balance = quantize_money(account.cash_balance - total_cost)
        position.quantity = new_quantity
        position.average_entry_price = average_entry_price.quantize(Decimal('0.0001'))
        position.status = PaperPositionStatus.OPEN
        if position.opened_at is None:
            position.opened_at = timezone.now()
        position.closed_at = None

    else:
        if position.quantity < quantity:
            raise PaperTradingRejectionError('Insufficient paper position quantity to execute sell trade.')

        proceeds = quantize_money(gross_amount - fees)
        realized_increment = quantize_money((price - position.average_entry_price) * quantity)
        remaining_quantity = quantize_quantity(position.quantity - quantity)

        account.cash_balance = quantize_money(account.cash_balance + proceeds)
        position.realized_pnl = quantize_money(position.realized_pnl + realized_increment)
        position.quantity = remaining_quantity
        if remaining_quantity <= ZERO:
            position.average_entry_price = Decimal('0.0000')
            position.status = PaperPositionStatus.CLOSED
            position.closed_at = timezone.now()
        else:
            position.status = PaperPositionStatus.OPEN

    position.save()
    revalue_position(position)
    account.save(update_fields=['cash_balance', 'updated_at'])
    revalue_account(account)

    trade = PaperTrade.objects.create(
        account=account,
        market=market,
        position=position,
        trade_type=trade_type,
        side=side,
        quantity=quantity,
        price=price,
        gross_amount=gross_amount,
        fees=fees,
        status=PaperTradeStatus.EXECUTED,
        notes=notes,
        metadata={
            'execution_mode': 'paper_demo_only',
            'market_data_source': market.source_type,
            'is_real_data': market.source_type == 'real_read_only',
            'price_source': price_resolution.source,
            **metadata,
        },
    )
    create_portfolio_snapshot(account=account)
    return ExecutionResult(account=account, position=position, trade=trade)

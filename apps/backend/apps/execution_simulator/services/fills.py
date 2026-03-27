from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from apps.execution_simulator.models import (
    PaperExecutionAttempt,
    PaperExecutionAttemptStatus,
    PaperFill,
    PaperFillType,
    PaperOrder,
)
from apps.execution_simulator.services.policies import PolicyConfig
from apps.paper_trading.services.market_pricing import resolve_market_price
from apps.paper_trading.services.valuation import quantize_quantity


@dataclass
class FillSimulationResult:
    status: str
    quantity: Decimal
    effective_price: Decimal | None
    slippage_bps: Decimal | None
    rationale: str


def _market_health(order: PaperOrder, policy: PolicyConfig) -> str:
    market = order.market
    liquidity = Decimal(str(market.liquidity or 0))
    spread_bps = int(market.spread_bps or 0)
    stale = bool((market.metadata or {}).get('stale'))
    degraded = bool((market.metadata or {}).get('degraded'))

    if stale or degraded:
        return 'poor'
    if liquidity >= policy.min_liquidity_for_auto_fill and spread_bps <= 120:
        return 'high'
    if liquidity >= (policy.min_liquidity_for_auto_fill / Decimal('2')) and spread_bps <= 250:
        return 'medium'
    return 'poor'


def simulate_fill(order: PaperOrder, policy: PolicyConfig) -> FillSimulationResult:
    health = _market_health(order, policy)
    order.wait_cycles += 1

    if order.cancel_after_n_cycles and order.wait_cycles >= order.cancel_after_n_cycles:
        return FillSimulationResult(
            status=PaperExecutionAttemptStatus.CANCELLED,
            quantity=Decimal('0.0000'),
            effective_price=None,
            slippage_bps=None,
            rationale='Order cancelled by policy wait-cycle limit.',
        )

    if order.expires_at and timezone.now() >= order.expires_at:
        return FillSimulationResult(
            status=PaperExecutionAttemptStatus.EXPIRED,
            quantity=Decimal('0.0000'),
            effective_price=None,
            slippage_bps=None,
            rationale='Order expired before fill.',
        )

    if order.wait_cycles > order.max_wait_cycles:
        return FillSimulationResult(
            status=PaperExecutionAttemptStatus.EXPIRED,
            quantity=Decimal('0.0000'),
            effective_price=None,
            slippage_bps=None,
            rationale='Order exceeded max wait cycles.',
        )

    snapshot = resolve_market_price(market=order.market, side='YES' if 'YES' in order.side else 'NO').price
    base_slippage = Decimal(str(policy.slippage_bps))

    if health == 'high':
        fill_qty = order.remaining_quantity
        slip = base_slippage / Decimal('2')
        status = PaperExecutionAttemptStatus.SUCCESS
    elif health == 'medium':
        fill_qty = quantize_quantity(order.remaining_quantity * policy.partial_fill_ratio)
        if fill_qty <= Decimal('0'):
            fill_qty = quantize_quantity(order.remaining_quantity)
        slip = base_slippage
        status = PaperExecutionAttemptStatus.PARTIAL if fill_qty < order.remaining_quantity else PaperExecutionAttemptStatus.SUCCESS
    else:
        fill_qty = Decimal('0.0000')
        slip = None
        status = PaperExecutionAttemptStatus.NO_FILL

    if fill_qty <= Decimal('0'):
        return FillSimulationResult(
            status=status,
            quantity=Decimal('0.0000'),
            effective_price=None,
            slippage_bps=None,
            rationale='No fill due to low liquidity/stale market conditions.',
        )

    direction = Decimal('1') if order.side in {'BUY_YES', 'BUY_NO'} else Decimal('-1')
    effective_price = (snapshot * (Decimal('1') + ((slip / Decimal('10000')) * direction))).quantize(Decimal('0.0001'))

    return FillSimulationResult(
        status=status,
        quantity=fill_qty,
        effective_price=effective_price,
        slippage_bps=slip,
        rationale=f'{health} liquidity profile simulated with policy {policy.slug}.',
    )


def create_attempt_and_fill(*, order: PaperOrder, result: FillSimulationResult):
    snapshot = resolve_market_price(market=order.market, side='YES' if 'YES' in order.side else 'NO').price
    attempt = PaperExecutionAttempt.objects.create(
        paper_order=order,
        attempt_status=result.status,
        market_price_snapshot=snapshot,
        effective_price=result.effective_price,
        filled_quantity=result.quantity,
        slippage_bps=result.slippage_bps,
        rationale=result.rationale,
        metadata={'policy_wait_cycles': order.wait_cycles},
    )

    fill = None
    if result.quantity > Decimal('0') and result.effective_price is not None:
        fill = PaperFill.objects.create(
            paper_order=order,
            fill_quantity=result.quantity,
            fill_price=result.effective_price,
            fill_type=PaperFillType.FULL if result.quantity >= order.remaining_quantity else PaperFillType.PARTIAL,
            metadata={'attempt_id': attempt.id},
        )
    return attempt, fill

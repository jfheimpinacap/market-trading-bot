from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.execution_simulator.models import PaperOrderCreatedFrom, PaperOrderSide, PaperOrderStatus
from apps.execution_simulator.services.lifecycle import run_execution_lifecycle
from apps.execution_simulator.services.orders import create_order
from apps.paper_trading.services.valuation import quantize_quantity


REPLAY_EXECUTION_MODE_NAIVE = 'naive'
REPLAY_EXECUTION_MODE_AWARE = 'execution_aware'


@dataclass
class ExecutionReplayTradeResult:
    filled_quantity: Decimal
    filled: bool
    partial: bool
    no_fill: bool
    slippage_bps_weighted: Decimal
    cancelled: bool
    expired: bool


def _proposal_to_order_side(*, trade_type: str, side: str) -> str:
    if trade_type == 'BUY' and side == 'YES':
        return PaperOrderSide.BUY_YES
    if trade_type == 'BUY' and side == 'NO':
        return PaperOrderSide.BUY_NO
    if trade_type == 'SELL' and side == 'YES':
        return PaperOrderSide.SELL_YES
    if trade_type == 'SELL' and side == 'NO':
        return PaperOrderSide.SELL_NO
    raise ValueError(f'Unsupported proposal trade mapping trade_type={trade_type} side={side}.')


def execute_replay_trade_with_execution_layer(
    *,
    replay_run_id: int,
    replay_step: int,
    market,
    trade_type: str,
    side: str,
    requested_quantity: Decimal,
    paper_account,
    execution_profile: str,
) -> ExecutionReplayTradeResult:
    if requested_quantity <= Decimal('0'):
        return ExecutionReplayTradeResult(
            filled_quantity=Decimal('0.0000'),
            filled=False,
            partial=False,
            no_fill=True,
            slippage_bps_weighted=Decimal('0'),
            cancelled=False,
            expired=False,
        )

    order = create_order(
        market=market,
        side=_proposal_to_order_side(trade_type=trade_type, side=side),
        requested_quantity=quantize_quantity(requested_quantity),
        created_from=PaperOrderCreatedFrom.OPPORTUNITY_SUPERVISOR,
        paper_account=paper_account,
        policy_profile=execution_profile,
        metadata={
            'replay_run_id': replay_run_id,
            'replay_step': replay_step,
            'execution_mode': REPLAY_EXECUTION_MODE_AWARE,
            'paper_demo_only': True,
            'real_execution_enabled': False,
        },
    )

    max_cycles = max(1, order.max_wait_cycles + 1)
    for _ in range(max_cycles):
        if order.status not in {PaperOrderStatus.OPEN, PaperOrderStatus.PARTIALLY_FILLED}:
            break
        run_execution_lifecycle(open_only=True, metadata={'replay_run_id': replay_run_id, 'replay_step': replay_step})
        order.refresh_from_db(fields=['status', 'remaining_quantity'])

    attempts = list(order.attempts.order_by('created_at', 'id'))
    fills = list(order.fills.order_by('created_at', 'id'))
    filled_quantity = sum((fill.fill_quantity for fill in fills), Decimal('0.0000'))
    weighted_slippage = Decimal('0')
    if filled_quantity > Decimal('0'):
        weighted_slippage = sum(
            (
                ((attempt.slippage_bps or Decimal('0')) * attempt.filled_quantity)
                for attempt in attempts
                if attempt.filled_quantity > Decimal('0')
            ),
            Decimal('0'),
        ) / filled_quantity

    return ExecutionReplayTradeResult(
        filled_quantity=filled_quantity,
        filled=filled_quantity >= order.requested_quantity,
        partial=filled_quantity > Decimal('0') and filled_quantity < order.requested_quantity,
        no_fill=filled_quantity <= Decimal('0'),
        slippage_bps_weighted=weighted_slippage,
        cancelled=order.status == PaperOrderStatus.CANCELLED,
        expired=order.status == PaperOrderStatus.EXPIRED,
    )


def build_execution_impact_summary(*, stats: dict) -> dict:
    orders = max(stats.get('orders_total', 0), 0)
    if orders == 0:
        return {
            'orders_total': 0,
            'fill_rate': 0.0,
            'partial_fill_rate': 0.0,
            'no_fill_rate': 0.0,
            'cancel_rate': 0.0,
            'order_expire_rate': 0.0,
            'avg_slippage_bps': 0.0,
            'avg_slippage_pct': 0.0,
            'execution_adjusted_pnl': str(stats.get('execution_adjusted_pnl', '0')),
            'naive_pnl': str(stats.get('naive_pnl', '0')),
            'execution_drag': str(stats.get('execution_drag', '0')),
            'execution_realism_score': 0.0,
            'execution_quality_bucket': 'NO_DATA',
        }

    fill_rate = stats.get('filled_orders', 0) / orders
    partial_fill_rate = stats.get('partial_orders', 0) / orders
    no_fill_rate = stats.get('no_fill_orders', 0) / orders
    cancel_rate = stats.get('cancelled_orders', 0) / orders
    order_expire_rate = stats.get('expired_orders', 0) / orders
    avg_slippage_bps = float(stats.get('slippage_sum_bps', Decimal('0')) / Decimal(orders))
    avg_slippage_pct = avg_slippage_bps / 10000

    realism_score = max(
        0.0,
        min(
            1.0,
            (fill_rate * 0.55)
            + ((1.0 - no_fill_rate) * 0.2)
            + ((1.0 - min(avg_slippage_bps / 150, 1.0)) * 0.15)
            + ((1.0 - cancel_rate - order_expire_rate) * 0.1),
        ),
    )

    if realism_score >= 0.75:
        quality_bucket = 'HIGH_FILL_RATE'
    elif no_fill_rate >= 0.35:
        quality_bucket = 'NO_FILL_RISK'
    elif avg_slippage_bps >= 60:
        quality_bucket = 'HIGH_SLIPPAGE'
    else:
        quality_bucket = 'BALANCED_EXECUTION'

    return {
        'orders_total': orders,
        'fill_rate': round(fill_rate, 4),
        'partial_fill_rate': round(partial_fill_rate, 4),
        'no_fill_rate': round(no_fill_rate, 4),
        'cancel_rate': round(cancel_rate, 4),
        'order_expire_rate': round(order_expire_rate, 4),
        'avg_slippage_bps': round(avg_slippage_bps, 2),
        'avg_slippage_pct': round(avg_slippage_pct, 6),
        'execution_adjusted_pnl': str(stats.get('execution_adjusted_pnl', '0')),
        'naive_pnl': str(stats.get('naive_pnl', '0')),
        'execution_drag': str(stats.get('execution_drag', '0')),
        'execution_realism_score': round(realism_score, 4),
        'execution_quality_bucket': quality_bucket,
    }

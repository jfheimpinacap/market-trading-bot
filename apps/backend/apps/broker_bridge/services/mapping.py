from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.execution_simulator.models import PaperOrder


@dataclass
class MappingResult:
    mapping_profile: str
    side: str
    order_type: str
    symbol: str
    market_ref: str


BROKER_SIDE_MAP = {
    'BUY_YES': 'BUY',
    'BUY_NO': 'BUY',
    'SELL_YES': 'SELL',
    'SELL_NO': 'SELL',
    'REDUCE': 'SELL',
    'CLOSE': 'SELL',
}


def pick_mapping_profile(*, source_type: str, created_from: str | None = None) -> str:
    if created_from == 'operator_queue':
        return 'conservative_manual_route'
    if source_type == 'paper_order':
        return 'generic_prediction_market'
    return 'generic_yes_no_contract'


def map_paper_order(order: PaperOrder) -> MappingResult:
    side = BROKER_SIDE_MAP.get(order.side, 'BUY')
    order_type = 'limit' if order.requested_price is not None else 'market'
    symbol = order.market.slug.upper().replace('-', '_')
    market_ref = order.market.slug
    mapping_profile = pick_mapping_profile(source_type='paper_order', created_from=order.created_from)
    return MappingResult(mapping_profile=mapping_profile, side=side, order_type=order_type, symbol=symbol, market_ref=market_ref)


def normalize_quantity(quantity: Decimal) -> Decimal:
    return quantity.quantize(Decimal('0.0001'))

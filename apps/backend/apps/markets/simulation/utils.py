from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

PROBABILITY_STEP = Decimal('0.0001')
MONEY_STEP = Decimal('0.0001')
PROBABILITY_MIN = Decimal('0.0100')
PROBABILITY_MAX = Decimal('0.9900')
PRICE_MIN = Decimal('0.0000')
PRICE_MAX = Decimal('100.0000')
ZERO = Decimal('0')
ONE = Decimal('1')
HUNDRED = Decimal('100')


def quantize_probability(value: Decimal) -> Decimal:
    return value.quantize(PROBABILITY_STEP, rounding=ROUND_HALF_UP)


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_STEP, rounding=ROUND_HALF_UP)


def clamp_decimal(value: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    return min(max(value, minimum), maximum)


def derive_price_pair(probability: Decimal) -> tuple[Decimal, Decimal]:
    bounded_probability = clamp_decimal(probability, PROBABILITY_MIN, PROBABILITY_MAX)
    yes_price = quantize_money(bounded_probability * HUNDRED)
    no_price = quantize_money((ONE - bounded_probability) * HUNDRED)
    return yes_price, no_price


def derive_order_book(yes_price: Decimal, spread_bps: int) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    spread = quantize_money(Decimal(spread_bps) / Decimal('10000') * HUNDRED)
    half_spread = quantize_money(spread / Decimal('2'))
    bid = quantize_money(clamp_decimal(yes_price - half_spread, PRICE_MIN, PRICE_MAX))
    ask = quantize_money(clamp_decimal(yes_price + half_spread, PRICE_MIN, PRICE_MAX))
    actual_spread = quantize_money(max(ZERO, ask - bid))
    last_price = quantize_money((bid + ask) / Decimal('2'))
    return bid, ask, actual_spread, last_price

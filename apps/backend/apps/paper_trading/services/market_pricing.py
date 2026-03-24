from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from apps.markets.models import Market, MarketSourceType, MarketStatus
from apps.paper_trading.models import PaperPositionSide

FOUR_DP = Decimal('0.0001')
ZERO = Decimal('0')
ONE = Decimal('1')
HUNDRED = Decimal('100')

TERMINAL_STATUSES = {
    MarketStatus.CLOSED,
    MarketStatus.RESOLVED,
    MarketStatus.CANCELLED,
    MarketStatus.ARCHIVED,
}


@dataclass(frozen=True)
class PaperTradabilityResult:
    is_tradable: bool
    code: str
    message: str
    is_real_data: bool
    source_type: str


@dataclass(frozen=True)
class PriceResolutionResult:
    price: Decimal | None
    source: str | None


class MarketPricingError(ValueError):
    """Raised when a market cannot provide a valid paper-trading mark price."""


def quantize_price(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(str(value or '0')).quantize(FOUR_DP, rounding=ROUND_HALF_UP)


def _normalize_probability(probability: Decimal | str | int | float | None) -> Decimal | None:
    if probability is None:
        return None
    normalized = Decimal(str(probability))
    if normalized < ZERO or normalized > ONE:
        return None
    return normalized.quantize(FOUR_DP, rounding=ROUND_HALF_UP)


def _is_valid_binary_price(price: Decimal | str | int | float | None) -> bool:
    if price is None:
        return False
    normalized = Decimal(str(price))
    return ZERO <= normalized <= HUNDRED


def get_paper_tradability(market: Market) -> PaperTradabilityResult:
    is_real_data = market.source_type == MarketSourceType.REAL_READ_ONLY

    if not market.is_active:
        return PaperTradabilityResult(
            is_tradable=False,
            code='MARKET_INACTIVE',
            message='This market is inactive and cannot be used for paper execution right now.',
            is_real_data=is_real_data,
            source_type=market.source_type,
        )

    if market.status in TERMINAL_STATUSES:
        return PaperTradabilityResult(
            is_tradable=False,
            code='MARKET_TERMINAL',
            message='This market is terminal and cannot be used for paper execution.',
            is_real_data=is_real_data,
            source_type=market.source_type,
        )

    if market.status == MarketStatus.PAUSED:
        return PaperTradabilityResult(
            is_tradable=False,
            code='MARKET_PAUSED',
            message='This market is paused and is not paper-tradable in its current status.',
            is_real_data=is_real_data,
            source_type=market.source_type,
        )

    if market.status != MarketStatus.OPEN:
        return PaperTradabilityResult(
            is_tradable=False,
            code='MARKET_NOT_OPEN',
            message=f'This market is in {market.status} status and is not currently paper-tradable.',
            is_real_data=is_real_data,
            source_type=market.source_type,
        )

    try:
        resolve_market_price(market=market, side=PaperPositionSide.YES)
        resolve_market_price(market=market, side=PaperPositionSide.NO)
    except MarketPricingError as exc:
        if is_real_data:
            message = 'This real market does not currently expose enough pricing data for paper trading.'
        else:
            message = str(exc)
        return PaperTradabilityResult(
            is_tradable=False,
            code='PRICE_UNAVAILABLE',
            message=message,
            is_real_data=is_real_data,
            source_type=market.source_type,
        )

    return PaperTradabilityResult(
        is_tradable=True,
        code='PAPER_TRADABLE',
        message='Market is paper-tradable. Execution remains simulated with virtual funds.',
        is_real_data=is_real_data,
        source_type=market.source_type,
    )


def resolve_market_price(market: Market, side: str) -> PriceResolutionResult:
    side = side.upper()
    probability = _normalize_probability(market.current_market_probability)

    if side == PaperPositionSide.YES:
        if _is_valid_binary_price(market.current_yes_price):
            return PriceResolutionResult(price=quantize_price(market.current_yes_price), source='current_yes_price')
        if probability is not None:
            return PriceResolutionResult(price=quantize_price(probability * HUNDRED), source='current_market_probability')
        raise MarketPricingError('No valid YES price or probability is available for this market.')

    if side == PaperPositionSide.NO:
        if _is_valid_binary_price(market.current_no_price):
            return PriceResolutionResult(price=quantize_price(market.current_no_price), source='current_no_price')
        if probability is not None:
            return PriceResolutionResult(price=quantize_price((ONE - probability) * HUNDRED), source='current_market_probability')
        raise MarketPricingError('No valid NO price or probability is available for this market.')

    raise MarketPricingError(f'Unsupported side for price resolution: {side}')

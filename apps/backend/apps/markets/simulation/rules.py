from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from random import Random

from django.utils import timezone

from apps.markets.models import Market, MarketStatus

from .utils import PROBABILITY_MAX, PROBABILITY_MIN

CATEGORY_VOLATILITY = {
    'politics': Decimal('0.0120'),
    'economics': Decimal('0.0095'),
    'sports': Decimal('0.0175'),
    'technology': Decimal('0.0140'),
    'geopolitics': Decimal('0.0100'),
}

STATUS_MOVEMENT_SCALE = {
    MarketStatus.OPEN: Decimal('1.00'),
    MarketStatus.PAUSED: Decimal('0.18'),
    MarketStatus.CLOSED: Decimal('0.04'),
}

TERMINAL_STATUSES = {MarketStatus.RESOLVED, MarketStatus.CANCELLED, MarketStatus.ARCHIVED}
SIMULATED_STATUSES = {MarketStatus.OPEN, MarketStatus.PAUSED, MarketStatus.CLOSED}


@dataclass(frozen=True)
class SimulationConfig:
    probability_min: Decimal = PROBABILITY_MIN
    probability_max: Decimal = PROBABILITY_MAX
    liquidity_min: Decimal = Decimal('0.0000')
    volume_24h_decay_floor: Decimal = Decimal('0.82')
    volume_24h_decay_ceiling: Decimal = Decimal('0.98')
    volume_24h_growth_ratio: Decimal = Decimal('0.0180')
    liquidity_shift_ratio: Decimal = Decimal('0.0250')
    max_spread_bps: int = 650
    min_spread_bps: int = 40
    paused_to_open_probability: Decimal = Decimal('0.12')
    open_to_paused_probability: Decimal = Decimal('0.015')
    early_close_probability: Decimal = Decimal('0.010')
    closed_to_resolved_probability: Decimal = Decimal('0.080')
    soon_close_window: timedelta = timedelta(hours=24)
    resolve_window: timedelta = timedelta(hours=6)
    demo_metadata_key: str = 'demo'
    category_volatility: dict[str, Decimal] = field(default_factory=lambda: CATEGORY_VOLATILITY.copy())


@dataclass(frozen=True)
class StatusDecision:
    next_status: str
    next_is_active: bool
    reason: str | None = None


def is_demo_market(market: Market, config: SimulationConfig) -> bool:
    return bool((market.metadata or {}).get(config.demo_metadata_key))


def is_terminal_status(status: str) -> bool:
    return status in TERMINAL_STATUSES


def category_volatility(market: Market, config: SimulationConfig) -> Decimal:
    return config.category_volatility.get(market.category.lower(), Decimal('0.0100'))


def time_pressure_multiplier(market: Market, now, config: SimulationConfig) -> Decimal:
    if not market.resolution_time:
        return Decimal('1.00')

    if market.resolution_time <= now:
        return Decimal('1.40')

    remaining = market.resolution_time - now
    if remaining <= timedelta(days=1):
        return Decimal('1.35')
    if remaining <= timedelta(days=7):
        return Decimal('1.20')
    if remaining <= timedelta(days=30):
        return Decimal('1.08')
    return Decimal('1.00')


def determine_next_status(market: Market, now, rng: Random, config: SimulationConfig) -> StatusDecision:
    status = market.status

    if status == MarketStatus.OPEN:
        if market.close_time and now >= market.close_time:
            return StatusDecision(next_status=MarketStatus.CLOSED, next_is_active=False, reason='close_time_reached')
        if market.close_time and market.close_time - now <= config.soon_close_window and rng.random() < float(config.early_close_probability):
            return StatusDecision(next_status=MarketStatus.CLOSED, next_is_active=False, reason='near_close_window')
        if rng.random() < float(config.open_to_paused_probability):
            return StatusDecision(next_status=MarketStatus.PAUSED, next_is_active=False, reason='temporary_pause')

    if status == MarketStatus.PAUSED:
        if market.close_time and now >= market.close_time:
            return StatusDecision(next_status=MarketStatus.CLOSED, next_is_active=False, reason='close_time_reached')
        if rng.random() < float(config.paused_to_open_probability):
            return StatusDecision(next_status=MarketStatus.OPEN, next_is_active=True, reason='resume_trading')

    if status == MarketStatus.CLOSED:
        if market.resolution_time and now >= market.resolution_time:
            return StatusDecision(next_status=MarketStatus.RESOLVED, next_is_active=False, reason='resolution_time_reached')
        if market.resolution_time and market.resolution_time - now <= config.resolve_window and rng.random() < float(config.closed_to_resolved_probability):
            return StatusDecision(next_status=MarketStatus.RESOLVED, next_is_active=False, reason='near_resolution_window')

    return StatusDecision(next_status=status, next_is_active=market.is_active)


def movement_scale(market: Market, now, config: SimulationConfig) -> Decimal:
    base = category_volatility(market, config)
    status_scale = STATUS_MOVEMENT_SCALE.get(market.status, Decimal('0.00'))
    return base * status_scale * time_pressure_multiplier(market, now, config)


def should_skip_market(market: Market, config: SimulationConfig) -> str | None:
    if not is_demo_market(market, config):
        return 'non_demo'
    if market.status in TERMINAL_STATUSES:
        return 'terminal_status'
    if market.status not in SIMULATED_STATUSES:
        return f'unsupported_status:{market.status}'
    return None

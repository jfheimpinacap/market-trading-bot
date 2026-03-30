from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from apps.markets.models import MarketStatus


@dataclass(frozen=True)
class StructuralThresholds:
    min_liquidity: Decimal = Decimal('3000')
    min_volume_24h: Decimal = Decimal('750')
    min_hours_to_resolution: int = 4
    max_hours_to_resolution: int = 24 * 240
    fresh_within_hours: int = 18


@dataclass
class FilterResult:
    open_ok: bool
    liquidity_score: Decimal
    volume_score: Decimal
    freshness_score: Decimal
    market_quality_score: Decimal
    time_to_resolution_hours: int | None
    reason_codes: list[str]
    blockers: list[str]


def _safe(value) -> Decimal:
    return Decimal(str(value or '0'))


def evaluate_structural_filters(*, market, now, thresholds: StructuralThresholds | None = None) -> FilterResult:
    t = thresholds or StructuralThresholds()
    reason_codes: list[str] = []
    blockers: list[str] = []

    open_ok = market.status == MarketStatus.OPEN
    if not open_ok:
        reason_codes.append('market_not_open')
        blockers.append('closed_or_not_open')

    liquidity = _safe(market.liquidity)
    volume = _safe(market.volume_24h)

    liquidity_score = min(Decimal('1'), liquidity / max(t.min_liquidity, Decimal('1')))
    volume_score = min(Decimal('1'), volume / max(t.min_volume_24h, Decimal('1')))
    if liquidity_score < Decimal('0.35'):
        reason_codes.append('low_liquidity')
    if volume_score < Decimal('0.35'):
        reason_codes.append('low_volume')

    resolution_hours = None
    if market.resolution_time:
        resolution_hours = int((market.resolution_time - now).total_seconds() / 3600)
        if resolution_hours < t.min_hours_to_resolution:
            reason_codes.append('bad_time_horizon_near_expiry')
            blockers.append('near_expiry')
        if resolution_hours > t.max_hours_to_resolution:
            reason_codes.append('bad_time_horizon_too_far')

    freshness_cutoff = now - timedelta(hours=t.fresh_within_hours)
    freshness_score = Decimal('1') if market.updated_at >= freshness_cutoff else Decimal('0.2')
    if freshness_score < Decimal('0.5'):
        reason_codes.append('stale_market_data')

    market_quality_score = Decimal('0.4')
    if market.current_market_probability is not None:
        market_quality_score += Decimal('0.25')
    if market.current_yes_price is not None or market.current_no_price is not None:
        market_quality_score += Decimal('0.20')
    if market.category:
        market_quality_score += Decimal('0.15')

    return FilterResult(
        open_ok=open_ok,
        liquidity_score=liquidity_score.quantize(Decimal('0.0001')),
        volume_score=volume_score.quantize(Decimal('0.0001')),
        freshness_score=freshness_score.quantize(Decimal('0.0001')),
        market_quality_score=min(Decimal('1'), market_quality_score).quantize(Decimal('0.0001')),
        time_to_resolution_hours=resolution_hours,
        reason_codes=reason_codes,
        blockers=blockers,
    )

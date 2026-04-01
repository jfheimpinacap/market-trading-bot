from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.markets.models import MarketStatus
from apps.research_agent.models import (
    ResearchLiquidityState,
    ResearchMarketActivityState,
    ResearchStructuralStatus,
    ResearchTimeWindowState,
    ResearchVolumeState,
)


@dataclass
class StructuralAssessmentResult:
    liquidity_state: str
    volume_state: str
    time_to_resolution_state: str
    market_activity_state: str
    structural_status: str
    reason_codes: list[str]
    summary: str
    metadata: dict


def _liquidity_state(value: Decimal | None) -> str:
    if value is None or value < Decimal('500'):
        return ResearchLiquidityState.INSUFFICIENT
    if value < Decimal('5000'):
        return ResearchLiquidityState.WEAK
    if value < Decimal('25000'):
        return ResearchLiquidityState.ADEQUATE
    return ResearchLiquidityState.STRONG


def _volume_state(value: Decimal | None) -> str:
    if value is None or value < Decimal('250'):
        return ResearchVolumeState.INSUFFICIENT
    if value < Decimal('2500'):
        return ResearchVolumeState.WEAK
    if value < Decimal('10000'):
        return ResearchVolumeState.ADEQUATE
    return ResearchVolumeState.STRONG


def _time_window_state(hours: int | None) -> str:
    if hours is None:
        return ResearchTimeWindowState.SHORT_WINDOW
    if hours < 8:
        return ResearchTimeWindowState.TOO_CLOSE
    if hours < 36:
        return ResearchTimeWindowState.SHORT_WINDOW
    if hours > 24 * 60:
        return ResearchTimeWindowState.TOO_FAR
    return ResearchTimeWindowState.GOOD_WINDOW


def assess_market_structure(*, market, now=None) -> StructuralAssessmentResult:
    now = now or timezone.now()
    reason_codes: list[str] = []

    liquidity_state = _liquidity_state(market.liquidity)
    volume_state = _volume_state(market.volume_24h)

    hours_to_resolution = None
    if market.resolution_time:
        hours_to_resolution = int((market.resolution_time - now).total_seconds() // 3600)
    time_state = _time_window_state(hours_to_resolution)

    activity_age = now - (market.updated_at or now)
    if market.status != MarketStatus.OPEN:
        activity_state = ResearchMarketActivityState.CLOSED_OR_BLOCKED
    elif activity_age > timedelta(days=5):
        activity_state = ResearchMarketActivityState.STALE
    elif activity_age > timedelta(days=2):
        activity_state = ResearchMarketActivityState.MODERATE
    else:
        activity_state = ResearchMarketActivityState.ACTIVE

    if market.status != MarketStatus.OPEN:
        reason_codes.append('market_not_open')
    if liquidity_state == ResearchLiquidityState.INSUFFICIENT:
        reason_codes.append('liquidity_insufficient')
    elif liquidity_state == ResearchLiquidityState.WEAK:
        reason_codes.append('liquidity_weak')
    if volume_state == ResearchVolumeState.INSUFFICIENT:
        reason_codes.append('volume_insufficient')
    elif volume_state == ResearchVolumeState.WEAK:
        reason_codes.append('volume_weak')
    if time_state == ResearchTimeWindowState.TOO_CLOSE:
        reason_codes.append('resolution_window_too_close')
    elif time_state == ResearchTimeWindowState.TOO_FAR:
        reason_codes.append('resolution_window_too_far')
    elif time_state == ResearchTimeWindowState.SHORT_WINDOW:
        reason_codes.append('resolution_window_short')
    if activity_state == ResearchMarketActivityState.STALE:
        reason_codes.append('market_stale')

    structural_status = ResearchStructuralStatus.WATCHLIST_ONLY
    if activity_state == ResearchMarketActivityState.CLOSED_OR_BLOCKED:
        structural_status = ResearchStructuralStatus.BLOCKED
    elif time_state in {ResearchTimeWindowState.TOO_CLOSE, ResearchTimeWindowState.TOO_FAR}:
        structural_status = ResearchStructuralStatus.DEFERRED
    elif liquidity_state in {ResearchLiquidityState.INSUFFICIENT} or volume_state in {ResearchVolumeState.INSUFFICIENT}:
        structural_status = ResearchStructuralStatus.BLOCKED
    elif liquidity_state == ResearchLiquidityState.WEAK or volume_state == ResearchVolumeState.WEAK or activity_state == ResearchMarketActivityState.STALE:
        structural_status = ResearchStructuralStatus.DEFERRED
    elif time_state == ResearchTimeWindowState.GOOD_WINDOW and activity_state in {
        ResearchMarketActivityState.ACTIVE,
        ResearchMarketActivityState.MODERATE,
    }:
        structural_status = ResearchStructuralStatus.PREDICTION_READY

    summary = (
        f'liquidity={liquidity_state}, volume={volume_state}, time_window={time_state}, '
        f'activity={activity_state}, structural_status={structural_status}'
    )
    return StructuralAssessmentResult(
        liquidity_state=liquidity_state,
        volume_state=volume_state,
        time_to_resolution_state=time_state,
        market_activity_state=activity_state,
        structural_status=structural_status,
        reason_codes=reason_codes,
        summary=summary,
        metadata={'time_to_resolution_hours': hours_to_resolution},
    )

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.markets.models import Market, MarketSnapshot
from apps.paper_trading.models import PaperAccount, PaperPositionStatus
from apps.paper_trading.services.portfolio import get_active_account
from apps.signals.models import MarketSignal, MarketSignalStatus, SignalDirection

ZERO = Decimal('0')


@dataclass
class ProposalContext:
    market: Market
    paper_account: PaperAccount | None
    latest_signals: list[MarketSignal]
    latest_snapshot: MarketSnapshot | None
    recent_snapshots: list[MarketSnapshot]
    bullish_count: int
    bearish_count: int
    neutral_count: int
    actionable_signal_count: int
    avg_signal_score: Decimal
    avg_signal_confidence: Decimal
    market_exposure_quantity: Decimal
    market_exposure_value: Decimal
    cash_balance: Decimal


def _average(values: list[Decimal]) -> Decimal:
    if not values:
        return ZERO
    return sum(values, ZERO) / Decimal(len(values))


def build_proposal_context(*, market: Market, paper_account: PaperAccount | None = None) -> ProposalContext:
    account = paper_account
    if account is None:
        account = get_active_account()

    latest_signals = list(
        MarketSignal.objects.filter(market=market, status__in=[MarketSignalStatus.ACTIVE, MarketSignalStatus.MONITOR])
        .order_by('-created_at', '-id')[:5]
    )

    recent_snapshots = list(
        MarketSnapshot.objects.filter(market=market)
        .order_by('-captured_at', '-id')[:5]
    )
    latest_snapshot = recent_snapshots[0] if recent_snapshots else None

    bullish_count = sum(1 for signal in latest_signals if signal.direction == SignalDirection.BULLISH)
    bearish_count = sum(1 for signal in latest_signals if signal.direction == SignalDirection.BEARISH)
    neutral_count = sum(1 for signal in latest_signals if signal.direction == SignalDirection.NEUTRAL)
    actionable_signal_count = sum(1 for signal in latest_signals if signal.is_actionable)

    avg_signal_score = _average([signal.score for signal in latest_signals])
    avg_signal_confidence = _average([signal.confidence for signal in latest_signals])

    market_exposure_quantity = ZERO
    market_exposure_value = ZERO
    cash_balance = ZERO

    if account is not None:
        open_positions = account.positions.filter(
            market=market,
            status=PaperPositionStatus.OPEN,
            quantity__gt=0,
        )
        market_exposure_quantity = sum((position.quantity for position in open_positions), ZERO)
        market_exposure_value = sum((position.market_value for position in open_positions), ZERO)
        cash_balance = account.cash_balance or ZERO

    return ProposalContext(
        market=market,
        paper_account=account,
        latest_signals=latest_signals,
        latest_snapshot=latest_snapshot,
        recent_snapshots=recent_snapshots,
        bullish_count=bullish_count,
        bearish_count=bearish_count,
        neutral_count=neutral_count,
        actionable_signal_count=actionable_signal_count,
        avg_signal_score=avg_signal_score,
        avg_signal_confidence=avg_signal_confidence,
        market_exposure_quantity=market_exposure_quantity,
        market_exposure_value=market_exposure_value,
        cash_balance=cash_balance,
    )

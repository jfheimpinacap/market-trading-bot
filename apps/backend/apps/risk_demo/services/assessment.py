from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from apps.markets.models import Market, MarketStatus
from apps.paper_trading.models import PaperPositionStatus, PaperPositionSide, PaperTradeType
from apps.paper_trading.services.portfolio import get_active_account
from apps.paper_trading.services.market_pricing import get_paper_tradability
from apps.paper_trading.services.valuation import PaperTradingValidationError, get_market_price
from apps.learning_memory.services import build_learning_influence
from apps.risk_demo.models import TradeRiskAssessment, TradeRiskDecision
from apps.signals.models import MarketSignal, MarketSignalStatus, SignalDirection

ZERO = Decimal('0')
ONE = Decimal('1')
HUNDRED = Decimal('100')

BLOCK_STATES = {
    MarketStatus.CLOSED,
    MarketStatus.RESOLVED,
    MarketStatus.CANCELLED,
    MarketStatus.ARCHIVED,
}


@dataclass
class WarningDraft:
    code: str
    severity: str
    message: str
    penalty: Decimal
    blocks: bool = False


def quantize_score(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def clamp(value: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    return max(minimum, min(value, maximum))


def _add_warning(target: list[WarningDraft], *, code: str, severity: str, message: str, penalty: str | Decimal, blocks: bool = False):
    target.append(
        WarningDraft(
            code=code,
            severity=severity,
            message=message,
            penalty=Decimal(str(penalty)),
            blocks=blocks,
        )
    )


def _signal_warnings(*, market: Market, trade_type: str, side: str, warnings: list[WarningDraft]) -> dict:
    recent_signals = list(
        MarketSignal.objects.filter(market=market, status__in=[MarketSignalStatus.ACTIVE, MarketSignalStatus.MONITOR])
        .order_by('-created_at', '-id')[:5]
    )
    actionable = any(signal.is_actionable for signal in recent_signals)
    bullish = sum(1 for signal in recent_signals if signal.direction == SignalDirection.BULLISH)
    bearish = sum(1 for signal in recent_signals if signal.direction == SignalDirection.BEARISH)

    trade_bias = None
    if trade_type == PaperTradeType.BUY and side == PaperPositionSide.YES:
        trade_bias = SignalDirection.BULLISH
    elif trade_type == PaperTradeType.BUY and side == PaperPositionSide.NO:
        trade_bias = SignalDirection.BEARISH
    elif trade_type == PaperTradeType.SELL and side == PaperPositionSide.YES:
        trade_bias = SignalDirection.BEARISH
    elif trade_type == PaperTradeType.SELL and side == PaperPositionSide.NO:
        trade_bias = SignalDirection.BULLISH

    if recent_signals and not actionable and trade_type == PaperTradeType.BUY:
        _add_warning(
            warnings,
            code='SIGNALS_NOT_ACTIONABLE',
            severity='medium',
            message='Recent demo signals for this market are monitor-only, so the guard suggests extra caution.',
            penalty='10',
        )

    if bullish > 0 and bearish > 0:
        _add_warning(
            warnings,
            code='CONTRADICTORY_SIGNALS',
            severity='medium',
            message='Recent demo signals disagree with each other, so the trade idea is less clear.',
            penalty='12',
        )

    if trade_bias == SignalDirection.BULLISH and bearish > bullish:
        _add_warning(
            warnings,
            code='SIGNAL_CONFLICT',
            severity='medium',
            message='Recent demo signals lean against this trade direction.',
            penalty='10',
        )
    elif trade_bias == SignalDirection.BEARISH and bullish > bearish:
        _add_warning(
            warnings,
            code='SIGNAL_CONFLICT',
            severity='medium',
            message='Recent demo signals lean against this trade direction.',
            penalty='10',
        )

    return {
        'recent_signal_count': len(recent_signals),
        'recent_signal_actionable': actionable,
        'bullish_signals': bullish,
        'bearish_signals': bearish,
    }


def assess_trade(*, market: Market, trade_type: str, side: str, quantity, requested_price=None, metadata: dict | None = None) -> TradeRiskAssessment:
    account = get_active_account()
    trade_type = trade_type.upper()
    side = side.upper()
    quantity = Decimal(str(quantity)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    metadata = metadata or {}

    warnings: list[WarningDraft] = []
    estimated_price = None
    if requested_price is not None:
        estimated_price = Decimal(str(requested_price)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    else:
        try:
            estimated_price = get_market_price(market=market, side=side)
        except PaperTradingValidationError as exc:
            _add_warning(
                warnings,
                code='PRICE_UNAVAILABLE',
                severity='high',
                message=str(exc),
                penalty='60',
                blocks=True,
            )

    estimated_cost = ZERO
    if estimated_price is not None:
        estimated_cost = (quantity * estimated_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    tradability = get_paper_tradability(market)
    if not tradability.is_tradable:
        _add_warning(
            warnings,
            code=tradability.code,
            severity='high',
            message=tradability.message,
            penalty='55',
            blocks=True,
        )

    if not market.is_active:
        _add_warning(
            warnings,
            code='MARKET_INACTIVE',
            severity='high',
            message='This market is inactive in the local demo and should not be traded right now.',
            penalty='50',
            blocks=True,
        )

    if market.status in BLOCK_STATES:
        _add_warning(
            warnings,
            code='MARKET_NOT_TRADABLE',
            severity='high',
            message=f'This market is not tradable because its status is {market.status}.',
            penalty='60',
            blocks=True,
        )
    elif market.status == MarketStatus.PAUSED:
        _add_warning(
            warnings,
            code='MARKET_PAUSED',
            severity='high',
            message='This market is paused in the local demo, so the guard blocks execution for now.',
            penalty='45',
            blocks=True,
        )

    if trade_type == PaperTradeType.BUY and estimated_price is not None and account.cash_balance < estimated_cost:
        _add_warning(
            warnings,
            code='INSUFFICIENT_CASH',
            severity='high',
            message='The estimated cost is higher than the available cash balance in the demo paper account.',
            penalty='65',
            blocks=True,
        )

    cash_balance = account.cash_balance or ZERO
    cost_ratio = ZERO if cash_balance <= ZERO else estimated_cost / cash_balance
    if cost_ratio >= Decimal('0.80'):
        _add_warning(
            warnings,
            code='VERY_LARGE_TRADE',
            severity='high',
            message='This trade would use most of the remaining demo cash balance.',
            penalty='35',
            blocks=trade_type == PaperTradeType.BUY,
        )
    elif cost_ratio >= Decimal('0.35'):
        _add_warning(
            warnings,
            code='LARGE_TRADE',
            severity='medium',
            message='This trade would use a large share of the current demo cash balance.',
            penalty='18',
        )

    open_positions = account.positions.filter(status=PaperPositionStatus.OPEN, quantity__gt=0)
    same_market_positions = list(open_positions.filter(market=market).select_related('market'))
    same_market_value = sum((position.market_value for position in same_market_positions), ZERO)
    same_market_quantity = sum((position.quantity for position in same_market_positions), ZERO)
    equity = account.equity or cash_balance
    concentration_ratio = ZERO if equity <= ZERO else (same_market_value + estimated_cost) / equity
    if concentration_ratio >= Decimal('0.45') or same_market_quantity >= Decimal('75.0000'):
        _add_warning(
            warnings,
            code='MARKET_CONCENTRATION',
            severity='medium',
            message='You already have meaningful exposure in this market, so adding more concentration deserves caution.',
            penalty='16',
        )

    spread_bps = Decimal(str(market.spread_bps or 0))
    liquidity = Decimal(str(market.liquidity or 0))
    volume_24h = Decimal(str(market.volume_24h or 0))
    if spread_bps >= Decimal('300'):
        _add_warning(
            warnings,
            code='WIDE_SPREAD',
            severity='medium',
            message='The spread is wide for this demo market, which makes the trade look less convenient.',
            penalty='12',
        )
    if liquidity < Decimal('25000'):
        _add_warning(
            warnings,
            code='LOW_LIQUIDITY',
            severity='medium',
            message='Liquidity is thin, so the market may not be a comfortable place for larger demo trades.',
            penalty='10',
        )
    if volume_24h < Decimal('1500'):
        _add_warning(
            warnings,
            code='LOW_ACTIVITY',
            severity='low',
            message='Recent market activity is light, so the guard marks this trade as less certain.',
            penalty='8',
        )

    signal_context = _signal_warnings(market=market, trade_type=trade_type, side=side, warnings=warnings)

    learning_influence = build_learning_influence(market=market, source_type=market.source_type)
    if learning_influence.caution_delta > Decimal('0.0000'):
        _add_warning(
            warnings,
            code='LEARNING_MEMORY_CAUTION',
            severity='medium',
            message='Recent heuristic learning memory suggests more conservative risk posture for this scope.',
            penalty=learning_influence.caution_delta * Decimal('100'),
        )

    if trade_type == PaperTradeType.SELL:
        matching_position = open_positions.filter(market=market, side=side).first()
        if matching_position is None or matching_position.quantity < quantity:
            _add_warning(
                warnings,
                code='INSUFFICIENT_POSITION',
                severity='high',
                message='The active demo account does not have enough position quantity to support this sell order.',
                penalty='65',
                blocks=True,
            )

    total_penalty = sum((warning.penalty for warning in warnings), ZERO)
    score = clamp(HUNDRED - total_penalty, ZERO, HUNDRED)
    is_blocked = any(warning.blocks for warning in warnings)
    if is_blocked:
        decision = TradeRiskDecision.BLOCK
    elif score < Decimal('70') or any(warning.severity in {'medium', 'high'} for warning in warnings):
        decision = TradeRiskDecision.CAUTION
    else:
        decision = TradeRiskDecision.APPROVE

    confidence = Decimal('0.82')
    if len(warnings) >= 3:
        confidence -= Decimal('0.14')
    elif len(warnings) >= 1:
        confidence -= Decimal('0.06')
    if not signal_context['recent_signal_actionable'] and signal_context['recent_signal_count'] > 0:
        confidence -= Decimal('0.05')
    if market.status != MarketStatus.OPEN:
        confidence -= Decimal('0.08')
    confidence = clamp(confidence, Decimal('0.35'), Decimal('0.95'))

    suggested_quantity = None
    if decision in {TradeRiskDecision.CAUTION, TradeRiskDecision.BLOCK} and trade_type == PaperTradeType.BUY:
        target_ratio = Decimal('0.25') if decision == TradeRiskDecision.CAUTION else Decimal('0.10')
        if estimated_price > ZERO and cash_balance > ZERO:
            suggested_quantity = ((cash_balance * target_ratio) / estimated_price).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            if suggested_quantity >= quantity:
                suggested_quantity = None

    warning_codes = {warning.code for warning in warnings}
    if decision == TradeRiskDecision.APPROVE:
        summary = 'Trade looks reasonable for the current demo context.'
    elif decision == TradeRiskDecision.CAUTION:
        summary = 'Trade is possible in the demo, but the guard found warnings worth reviewing first.'
    elif {'MARKET_TERMINAL', 'MARKET_PAUSED', 'MARKET_INACTIVE', 'MARKET_NOT_OPEN'} & warning_codes:
        summary = 'Trade is blocked because this market is not tradable in paper mode right now.'
    else:
        summary = 'Trade is blocked by the demo guard because the market or account context is not suitable.'

    rationale_parts = [
        f'Estimated price {(f"{estimated_price:.4f}" if estimated_price is not None else "n/a")} and gross amount {estimated_cost:.2f} were compared against demo cash {cash_balance:.2f}.',
        f'Market status is {market.status} with spread {int(spread_bps)} bps, liquidity {liquidity:.0f}, and 24h volume {volume_24h:.0f}.',
    ]
    if same_market_positions:
        rationale_parts.append(
            f'The account already has {same_market_quantity:.4f} contracts in this market across {len(same_market_positions)} open position(s).'
        )
    if signal_context['recent_signal_count']:
        rationale_parts.append(
            'Recent demo signals were checked for actionability and directional agreement before returning the verdict.'
        )
    else:
        rationale_parts.append('No recent demo signals were available, so the guard relied only on market and account context.')
    if suggested_quantity is not None:
        rationale_parts.append(f'A smaller demo size near {suggested_quantity:.4f} contracts would fit the guardrails better.')

    assessment = TradeRiskAssessment.objects.create(
        market=market,
        paper_account=account,
        side=side,
        trade_type=trade_type,
        quantity=quantity,
        requested_price=requested_price,
        current_market_probability=market.current_market_probability,
        current_yes_price=market.current_yes_price,
        current_no_price=market.current_no_price,
        decision=decision,
        score=quantize_score(score),
        confidence=quantize_score(confidence),
        summary=summary,
        rationale=' '.join(rationale_parts),
        warnings=[
            {
                'code': warning.code,
                'severity': warning.severity,
                'message': warning.message,
            }
            for warning in warnings
        ],
        suggested_quantity=suggested_quantity,
        is_actionable=decision != TradeRiskDecision.BLOCK,
        metadata={
            'estimated_price': f'{estimated_price:.4f}',
            'estimated_cost': f'{estimated_cost:.2f}',
            'cash_balance': f'{cash_balance:.2f}',
            'cost_ratio': f'{cost_ratio:.4f}',
            'concentration_ratio': f'{concentration_ratio:.4f}',
            'signal_context': signal_context,
            'learning_influence': {
                'confidence_delta': str(learning_influence.confidence_delta),
                'quantity_multiplier': str(learning_influence.quantity_multiplier),
                'caution_delta': str(learning_influence.caution_delta),
                'reasons': learning_influence.reasons,
            },
            **metadata,
        },
    )
    return assessment

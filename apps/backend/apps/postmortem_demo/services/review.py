from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.markets.models import Market, MarketStatus
from apps.paper_trading.models import PaperTrade, PaperTradeStatus, PaperTradeType
from apps.postmortem_demo.models import TradeReview, TradeReviewOutcome, TradeReviewStatus
from apps.risk_demo.models import TradeRiskAssessment, TradeRiskDecision
from apps.signals.models import MarketSignal, SignalDirection

ZERO = Decimal('0.00')
PRICE_THRESHOLD = Decimal('3.00')
NEUTRAL_THRESHOLD = Decimal('1.00')
ONE_HUNDRED = Decimal('100.00')


@dataclass
class ReviewGenerationResult:
    review: TradeReview
    created: bool
    stale_marked: bool = False


@dataclass
class ReviewContext:
    current_price: Decimal
    price_delta: Decimal
    signed_move: Decimal
    pnl_estimate: Decimal
    outcome: str
    score: Decimal
    confidence: Decimal
    summary: str
    rationale: str
    lesson: str
    recommendation: str
    review_status: str
    risk_decision: str
    signals_context: list[dict]
    metadata: dict


def _quantize_price(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def _quantize_money(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _quantize_ratio(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _get_trade_side_price(market: Market, side: str) -> Decimal:
    if side == 'YES':
        if market.current_yes_price is not None:
            return _quantize_price(market.current_yes_price)
        probability = market.current_market_probability or Decimal('0')
        return _quantize_price(probability * ONE_HUNDRED)

    if market.current_no_price is not None:
        return _quantize_price(market.current_no_price)
    probability = market.current_market_probability or Decimal('0')
    return _quantize_price((Decimal('1') - probability) * ONE_HUNDRED)


def _get_trade_probability_at_execution(trade: PaperTrade) -> Decimal | None:
    probability = trade.metadata.get('market_probability_at_trade') if trade.metadata else None
    if probability is not None:
        return Decimal(str(probability)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

    latest_snapshot = trade.market.snapshots.filter(captured_at__lte=trade.executed_at).order_by('-captured_at', '-id').first()
    if latest_snapshot and latest_snapshot.market_probability is not None:
        return latest_snapshot.market_probability

    return trade.market.current_market_probability


def _latest_trade_signal(trade: PaperTrade) -> MarketSignal | None:
    return (
        MarketSignal.objects.filter(market=trade.market, created_at__lte=trade.executed_at)
        .select_related('agent')
        .order_by('-created_at', '-id')
        .first()
    )


def _trade_risk_assessment(trade: PaperTrade) -> TradeRiskAssessment | None:
    risk_assessment_id = (trade.metadata or {}).get('risk_assessment_id')
    if risk_assessment_id:
        return TradeRiskAssessment.objects.filter(pk=risk_assessment_id).select_related('market', 'paper_account').first()

    return (
        TradeRiskAssessment.objects.filter(
            market=trade.market,
            paper_account=trade.account,
            side=trade.side,
            trade_type=trade.trade_type,
            quantity=trade.quantity,
            created_at__lte=trade.executed_at,
        )
        .select_related('market', 'paper_account')
        .order_by('-created_at', '-id')
        .first()
    )


def _get_signal_context(signal: MarketSignal | None, trade: PaperTrade) -> tuple[list[dict], list[str], list[str], str | None]:
    context: list[dict] = []
    rationale_bits: list[str] = []
    lesson_bits: list[str] = []
    signal_alignment: str | None = None

    if signal is None:
        return context, rationale_bits, lesson_bits, signal_alignment

    expected_direction = 'BULLISH' if trade.side == 'YES' else 'BEARISH'
    aligned = signal.direction == expected_direction
    signal_alignment = 'aligned' if aligned else 'against'
    context.append(
        {
            'signal_id': signal.id,
            'headline': signal.headline,
            'direction': signal.direction,
            'status': signal.status,
            'is_actionable': signal.is_actionable,
            'score': str(signal.score),
            'confidence': str(signal.confidence),
        }
    )

    if signal.is_actionable:
        rationale_bits.append(f'The latest demo signal was actionable and {signal_alignment} the trade direction.')
    else:
        rationale_bits.append('The latest demo signal was monitor-only, so the trade had weaker signal support.')
        lesson_bits.append('Treat monitor-only signals as context, not conviction, before sizing up a paper trade.')

    if not aligned and signal.direction != SignalDirection.NEUTRAL:
        rationale_bits.append('The trade went against the most recent signal direction for this market.')
        lesson_bits.append('When a new trade goes against the latest signal, keep the size small and require a stronger manual thesis.')

    return context, rationale_bits, lesson_bits, signal_alignment


def _get_risk_context(risk_assessment: TradeRiskAssessment | None) -> tuple[list[str], list[str], str]:
    rationale_bits: list[str] = []
    lesson_bits: list[str] = []
    risk_decision = ''

    if risk_assessment is None:
        return rationale_bits, lesson_bits, risk_decision

    risk_decision = risk_assessment.decision
    rationale_bits.append(f'The latest risk check at trade time returned {risk_assessment.decision.lower()}.')

    if risk_assessment.decision == TradeRiskDecision.CAUTION:
        lesson_bits.append('A caution verdict usually means the setup was tradable, but not clean enough for aggressive size.')
    elif risk_assessment.decision == TradeRiskDecision.BLOCK:
        lesson_bits.append('This trade was executed despite a block verdict in the demo risk guard, so the review keeps that warning visible.')

    return rationale_bits, lesson_bits, risk_decision


def build_trade_review_context(trade: PaperTrade) -> ReviewContext:
    current_price = _get_trade_side_price(trade.market, trade.side)
    entry_price = _quantize_price(trade.price) or Decimal('0.0000')
    price_delta = _quantize_price(current_price - entry_price) or Decimal('0.0000')
    signed_move = price_delta if trade.trade_type == PaperTradeType.BUY else _quantize_price(entry_price - current_price) or Decimal('0.0000')
    pnl_estimate = _quantize_money((signed_move * trade.quantity) - trade.fees) or ZERO

    if signed_move >= PRICE_THRESHOLD:
        outcome = TradeReviewOutcome.FAVORABLE
    elif signed_move <= -PRICE_THRESHOLD:
        outcome = TradeReviewOutcome.UNFAVORABLE
    else:
        outcome = TradeReviewOutcome.NEUTRAL

    signal = _latest_trade_signal(trade)
    risk_assessment = _trade_risk_assessment(trade)
    signal_context, signal_rationale, signal_lessons, signal_alignment = _get_signal_context(signal, trade)
    risk_rationale, risk_lessons, risk_decision = _get_risk_context(risk_assessment)

    rationale_bits = [
        f'Trade entry price was {entry_price} and the latest market price for the traded side is {current_price}.',
        f'That implies a signed move of {signed_move} points for this {trade.trade_type.lower()} trade.',
    ]
    lesson_bits: list[str] = []
    recommendation_bits: list[str] = []
    metadata: dict[str, object] = {
        'heuristics_version': 'postmortem-demo-v1',
        'market_status': trade.market.status,
        'trade_notional_ratio': '0.00',
    }

    rationale_bits.extend(signal_rationale)
    rationale_bits.extend(risk_rationale)
    lesson_bits.extend(signal_lessons)
    lesson_bits.extend(risk_lessons)

    account_equity = trade.account.equity or trade.account.initial_balance or Decimal('1')
    notional_ratio = (trade.gross_amount / account_equity) if account_equity else Decimal('0')
    metadata['trade_notional_ratio'] = str(_quantize_ratio(notional_ratio * Decimal('100')))
    if notional_ratio >= Decimal('0.20'):
        rationale_bits.append('The trade used a relatively large portion of the demo account equity.')
        lesson_bits.append('Large paper trades can hide sizing mistakes, so keep demo exposure smaller until the thesis is clearer.')

    if trade.market.status in {MarketStatus.PAUSED, MarketStatus.CLOSED, MarketStatus.RESOLVED, MarketStatus.CANCELLED, MarketStatus.ARCHIVED}:
        rationale_bits.append(f'The market is now in a {trade.market.status.lower()} state, which limits how much follow-through can still happen.')
        lesson_bits.append('Post-trade reviews should note when the market lifecycle changes quickly after execution.')

    score = Decimal('50.00') + (signed_move * Decimal('5'))
    if signal and not signal.is_actionable:
        score -= Decimal('8.00')
    if signal_alignment == 'against':
        score -= Decimal('10.00')
    if risk_decision == TradeRiskDecision.CAUTION:
        score -= Decimal('7.00')
    elif risk_decision == TradeRiskDecision.BLOCK:
        score -= Decimal('15.00')
    if notional_ratio >= Decimal('0.20'):
        score -= Decimal('6.00')

    score = min(Decimal('100.00'), max(Decimal('0.00'), _quantize_ratio(score)))
    confidence = Decimal('0.45') + (min(abs(signed_move), Decimal('8.00')) / Decimal('20'))
    if risk_decision == TradeRiskDecision.BLOCK:
        confidence += Decimal('0.05')
    confidence = min(Decimal('0.95'), max(Decimal('0.20'), _quantize_ratio(confidence)))

    if outcome == TradeReviewOutcome.FAVORABLE:
        summary = 'The trade is currently favorable because the market moved in the intended direction after execution.'
        recommendation_bits.append('Keep using this review as confirmation only; the demo engine is not forecasting future performance.')
    elif outcome == TradeReviewOutcome.UNFAVORABLE:
        summary = 'The trade is currently unfavorable because the market moved against the executed side after the fill.'
        recommendation_bits.append('Review entry timing and sizing before repeating a similar paper trade.')
    else:
        summary = 'The trade is currently neutral because the market has barely moved since execution.'
        recommendation_bits.append('Wait for clearer follow-through before treating a flat demo trade as a validated idea.')

    if risk_decision == TradeRiskDecision.BLOCK:
        recommendation_bits.append('Do not treat this as a model miss yet; the main lesson is that the trade bypassed the demo risk guard.')
    elif risk_decision == TradeRiskDecision.CAUTION:
        recommendation_bits.append('If a future trade receives a caution verdict again, consider trimming size or waiting for a cleaner signal.')

    if signal and not signal.is_actionable:
        recommendation_bits.append('Prefer actionable signals over monitor-only signals when you want the review loop to stay coherent.')

    if not lesson_bits:
        lesson_bits.append('Use post-mortem reviews to compare thesis quality, sizing, and market follow-through instead of chasing precision.')

    market_probability_at_trade = _get_trade_probability_at_execution(trade)
    market_probability_now = trade.market.current_market_probability

    return ReviewContext(
        current_price=current_price,
        price_delta=price_delta,
        signed_move=signed_move,
        pnl_estimate=pnl_estimate,
        outcome=outcome,
        score=score,
        confidence=confidence,
        summary=summary,
        rationale=' '.join(rationale_bits),
        lesson=' '.join(lesson_bits),
        recommendation=' '.join(recommendation_bits),
        review_status=TradeReviewStatus.REVIEWED,
        risk_decision=risk_decision,
        signals_context=signal_context,
        metadata=metadata,
    )


@transaction.atomic
def generate_trade_review(trade: PaperTrade, *, refresh_existing: bool = False) -> ReviewGenerationResult:
    review = TradeReview.objects.filter(paper_trade=trade).select_related('market').first()
    stale_marked = False

    if review and not refresh_existing:
        if review.reviewed_at and trade.market.updated_at and trade.market.updated_at > review.reviewed_at:
            review.review_status = TradeReviewStatus.STALE
            review.save(update_fields=['review_status', 'updated_at'])
            stale_marked = True
        return ReviewGenerationResult(review=review, created=False, stale_marked=stale_marked)

    context = build_trade_review_context(trade)
    defaults = {
        'paper_account': trade.account,
        'market': trade.market,
        'review_status': context.review_status,
        'outcome': context.outcome,
        'score': context.score,
        'confidence': context.confidence,
        'summary': context.summary,
        'rationale': context.rationale,
        'lesson': context.lesson,
        'recommendation': context.recommendation,
        'entry_price': _quantize_price(trade.price),
        'current_market_price': context.current_price,
        'price_delta': context.price_delta,
        'pnl_estimate': context.pnl_estimate,
        'market_probability_at_trade': _get_trade_probability_at_execution(trade),
        'market_probability_now': trade.market.current_market_probability,
        'signals_context': context.signals_context,
        'risk_decision_at_trade': context.risk_decision,
        'reviewed_at': timezone.now(),
        'metadata': context.metadata,
    }

    review, created = TradeReview.objects.update_or_create(paper_trade=trade, defaults=defaults)
    return ReviewGenerationResult(review=review, created=created, stale_marked=False)


def generate_trade_reviews(*, trade_id: int | None = None, limit: int | None = None, refresh_existing: bool = False) -> list[ReviewGenerationResult]:
    queryset: QuerySet[PaperTrade] = PaperTrade.objects.filter(status=PaperTradeStatus.EXECUTED).select_related('account', 'market')

    if trade_id is not None:
        queryset = queryset.filter(pk=trade_id)

    queryset = queryset.order_by('-executed_at', '-id')
    if limit is not None:
        queryset = queryset[:limit]

    return [generate_trade_review(trade, refresh_existing=refresh_existing) for trade in queryset]

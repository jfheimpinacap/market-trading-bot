from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from apps.learning_memory.services import build_learning_influence
from apps.paper_trading.models import PaperPositionSide, PaperTradeType
from apps.paper_trading.services.valuation import PaperTradingValidationError, get_market_price
from apps.policy_engine.models import ApprovalDecision, ApprovalDecisionType, PolicyRequestedBy, PolicyTriggeredFrom
from apps.policy_engine.services import evaluate_trade_policy
from apps.proposal_engine.models import ProposalDirection
from apps.proposal_engine.services.context import ProposalContext
from apps.risk_agent.services import run_risk_assessment, run_risk_sizing
from apps.risk_demo.models import TradeRiskAssessment, TradeRiskDecision
from apps.risk_demo.services.assessment import assess_trade

ZERO = Decimal('0')
ONE = Decimal('1')
HUNDRED = Decimal('100')
HOLD_TRADE_TYPE = "HOLD"


@dataclass
class HeuristicResult:
    direction: str
    headline: str
    thesis: str
    rationale: str
    suggested_trade_type: str
    suggested_side: str | None
    suggested_price_reference: Decimal | None
    proposal_score: Decimal
    confidence: Decimal
    suggested_quantity: Decimal
    risk_assessment: TradeRiskAssessment
    policy_decision: ApprovalDecision
    approval_required: bool
    is_actionable: bool
    recommendation: str


def clamp(value: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    return max(minimum, min(value, maximum))


def q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def q4(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def _build_trade_idea(context: ProposalContext) -> tuple[str, str, str, str, str | None, Decimal | None, Decimal, Decimal]:
    market = context.market
    bullish = context.bullish_count
    bearish = context.bearish_count
    actionable = context.actionable_signal_count

    score = Decimal('42.00')
    confidence = Decimal('0.45')

    if actionable >= 1 and bullish >= bearish + 1:
        direction = ProposalDirection.BUY_YES
        trade_type = PaperTradeType.BUY
        side = PaperPositionSide.YES
        try:
            price_ref = get_market_price(market=market, side=PaperPositionSide.YES)
        except PaperTradingValidationError:
            price_ref = None
        score = Decimal('70.00') + (Decimal(actionable) * Decimal('5.00'))
        confidence = Decimal('0.55') + (context.avg_signal_confidence * Decimal('0.30'))
    elif actionable >= 1 and bearish >= bullish + 1:
        direction = ProposalDirection.BUY_NO
        trade_type = PaperTradeType.BUY
        side = PaperPositionSide.NO
        try:
            price_ref = get_market_price(market=market, side=PaperPositionSide.NO)
        except PaperTradingValidationError:
            price_ref = None
        score = Decimal('70.00') + (Decimal(actionable) * Decimal('5.00'))
        confidence = Decimal('0.55') + (context.avg_signal_confidence * Decimal('0.30'))
    elif bullish > 0 and bearish > 0:
        direction = ProposalDirection.HOLD
        trade_type = HOLD_TRADE_TYPE
        side = None
        price_ref = None
        score = Decimal('48.00')
        confidence = Decimal('0.42')
    else:
        direction = ProposalDirection.AVOID
        trade_type = HOLD_TRADE_TYPE
        side = None
        price_ref = None
        score = Decimal('35.00')
        confidence = Decimal('0.38')

    if context.latest_prediction_score is not None:
        prediction = context.latest_prediction_score
        edge = Decimal(str(prediction.edge))
        edge_confidence = Decimal(str(prediction.confidence))
        score += edge * Decimal('120')
        confidence += max(Decimal('-0.10'), min(edge * Decimal('0.60'), Decimal('0.10')))
        confidence += max(Decimal('-0.05'), min((edge_confidence - Decimal('0.50')) * Decimal('0.30'), Decimal('0.05')))

    thesis = (
        f'Señales demo recientes: bullish={bullish}, bearish={bearish}, '
        f'actionable={actionable}. Probabilidad actual={market.current_market_probability}.'
    )
    if context.latest_prediction_score is not None:
        thesis = (
            f'{thesis} Prediction agent: system={context.latest_prediction_score.system_probability}, '
            f'market={context.latest_prediction_score.market_probability}, edge={context.latest_prediction_score.edge}, '
            f'confidence={context.latest_prediction_score.confidence}.'
        )
    rationale = (
        'La propuesta usa una heurística local-first: si señales accionables se alinean se sugiere BUY, '
        'si están mezcladas se sugiere HOLD, y sin claridad se sugiere AVOID.'
    )
    headline = f'{market.title}: propuesta {direction} basada en señales demo y guardrails.'

    return direction, headline, thesis, rationale, trade_type, side, price_ref, q2(clamp(score, ZERO, HUNDRED)), q2(clamp(confidence, Decimal('0.00'), ONE))


def _compute_quantity(*, context: ProposalContext, confidence: Decimal, trade_type: str, side: str | None, suggested_price_reference: Decimal | None) -> Decimal:
    if trade_type == HOLD_TRADE_TYPE:
        return Decimal('0.0000')

    cash = context.cash_balance
    if cash <= ZERO:
        return Decimal('0.0000')

    base_budget = min(Decimal('150.00'), cash * Decimal('0.05'))
    confidence_multiplier = Decimal('0.70') + (confidence * Decimal('0.60'))
    budget = base_budget * confidence_multiplier

    if context.market_exposure_quantity >= Decimal('40.0000'):
        budget *= Decimal('0.50')
    elif context.market_exposure_quantity >= Decimal('20.0000'):
        budget *= Decimal('0.75')

    if side is None:
        return Decimal('0.0000')

    price = suggested_price_reference
    if price is None:
        try:
            price = get_market_price(market=context.market, side=side)
        except PaperTradingValidationError:
            return Decimal('0.0000')
    if price <= ZERO:
        return Decimal('0.0000')

    quantity = budget / price
    return q4(clamp(quantity, Decimal('1.0000'), Decimal('250.0000')))


def evaluate_proposal_heuristics(*, context: ProposalContext, triggered_from: str) -> HeuristicResult:
    (
        direction,
        headline,
        thesis,
        rationale,
        suggested_trade_type,
        suggested_side,
        suggested_price_reference,
        proposal_score,
        confidence,
    ) = _build_trade_idea(context)

    learning_influence = build_learning_influence(
        market=context.market,
        signal_type=context.latest_signals[0].signal_type if context.latest_signals else None,
        source_type=context.market.source_type,
    )

    confidence = clamp(confidence + learning_influence.confidence_delta, Decimal('0.25'), ONE)

    suggested_quantity = _compute_quantity(
        context=context,
        confidence=confidence,
        trade_type=suggested_trade_type,
        side=suggested_side,
        suggested_price_reference=suggested_price_reference,
    )

    suggested_quantity = q4(suggested_quantity * learning_influence.quantity_multiplier)

    risk_assessment = assess_trade(
        market=context.market,
        trade_type=PaperTradeType.BUY if suggested_trade_type == HOLD_TRADE_TYPE else suggested_trade_type,
        side=suggested_side or PaperPositionSide.YES,
        quantity=suggested_quantity if suggested_quantity > ZERO else Decimal('1.0000'),
        requested_price=suggested_price_reference,
        metadata={
            'proposal_engine': {
                'direction': direction,
                'triggered_from': triggered_from,
            }
        },
    )

    if risk_assessment.decision == TradeRiskDecision.CAUTION:
        suggested_quantity = q4(suggested_quantity * Decimal('0.60')) if suggested_quantity > ZERO else suggested_quantity
    elif risk_assessment.decision == TradeRiskDecision.BLOCK:
        suggested_quantity = Decimal('0.0000')

    risk_agent_assessment = run_risk_assessment(
        market=context.market,
        prediction_score=context.latest_prediction_score,
        metadata={'triggered_from': triggered_from, 'from': 'proposal_engine'},
    )
    risk_agent_sizing = run_risk_sizing(
        risk_assessment=risk_agent_assessment,
        base_quantity=suggested_quantity if suggested_quantity > ZERO else Decimal('0.0000'),
        metadata={
            'source': 'proposal_engine',
            'reference_price': str(suggested_price_reference or Decimal('1.0'))
        },
    )
    suggested_quantity = risk_agent_sizing.adjusted_quantity
    risk_assessment.metadata = {
        **(risk_assessment.metadata or {}),
        'risk_agent_assessment_id': risk_agent_assessment.id,
        'risk_agent_sizing_id': risk_agent_sizing.id,
    }
    risk_assessment.save(update_fields=['metadata', 'updated_at'])

    normalized_triggered_from = triggered_from
    if normalized_triggered_from == 'signals':
        normalized_triggered_from = PolicyTriggeredFrom.SIGNAL
    elif normalized_triggered_from == 'dashboard':
        normalized_triggered_from = PolicyTriggeredFrom.SYSTEM

    policy_decision = evaluate_trade_policy(
        market=context.market,
        trade_type=PaperTradeType.BUY if suggested_trade_type == HOLD_TRADE_TYPE else suggested_trade_type,
        side=suggested_side or PaperPositionSide.YES,
        quantity=suggested_quantity if suggested_quantity > ZERO else Decimal('1.0000'),
        requested_price=suggested_price_reference,
        triggered_from=normalized_triggered_from,
        requested_by=PolicyRequestedBy.SYSTEM,
        risk_assessment=risk_assessment,
        metadata={
            'proposal_engine': {
                'direction': direction,
                'triggered_from': triggered_from,
            }
        },
    )

    approval_required = policy_decision.decision == ApprovalDecisionType.APPROVAL_REQUIRED
    is_actionable = (
        direction in {ProposalDirection.BUY_YES, ProposalDirection.BUY_NO}
        and suggested_quantity > ZERO
        and risk_assessment.decision != TradeRiskDecision.BLOCK
        and policy_decision.decision != ApprovalDecisionType.HARD_BLOCK
    )

    if learning_influence.reasons:
        rationale = f"{rationale} Learning memory influence: {'; '.join(learning_influence.reasons[:3])}."

    if policy_decision.decision == ApprovalDecisionType.HARD_BLOCK:
        recommendation = 'No ejecutar: policy devolvió HARD_BLOCK. Revisar reglas y contexto antes de intentar de nuevo.'
    elif risk_assessment.decision == TradeRiskDecision.CAUTION:
        recommendation = 'Propuesta válida con cautela: reducir tamaño y confirmar manualmente antes de ejecutar.'
    elif direction in {ProposalDirection.HOLD, ProposalDirection.AVOID}:
        recommendation = 'No hay edge claro ahora: mantener observación hasta nuevas señales demo accionables.'
    else:
        recommendation = 'Propuesta accionable para paper trading demo bajo guardrails actuales.'

    if learning_influence.reasons and 'cautela' not in recommendation.lower():
        recommendation = f"{recommendation} Ajuste conservador aplicado por learning memory heurístico."

    recommendation = f"{recommendation} Risk agent sizing_mode={risk_agent_sizing.sizing_mode} adjusted_qty={risk_agent_sizing.adjusted_quantity}."

    return HeuristicResult(
        direction=direction,
        headline=headline,
        thesis=thesis,
        rationale=rationale,
        suggested_trade_type=suggested_trade_type,
        suggested_side=suggested_side,
        suggested_price_reference=suggested_price_reference,
        proposal_score=proposal_score,
        confidence=confidence,
        suggested_quantity=suggested_quantity,
        risk_assessment=risk_assessment,
        policy_decision=policy_decision,
        approval_required=approval_required,
        is_actionable=is_actionable,
        recommendation=recommendation,
    )

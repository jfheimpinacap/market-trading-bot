from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from apps.paper_trading.services.portfolio import get_active_account
from apps.risk_agent.models import RiskAssessment, RiskLevel, RiskSizingDecision, RiskSizingMode


def _q4(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.0001'), rounding=ROUND_DOWN)


def run_risk_sizing(*, risk_assessment: RiskAssessment, base_quantity: Decimal, metadata: dict | None = None) -> RiskSizingDecision:
    metadata = metadata or {}
    base_quantity = Decimal(str(base_quantity))
    account = get_active_account()

    confidence_adj = Decimal('1.0000')
    liquidity_adj = Decimal('1.0000')
    safety_adj = Decimal('1.0000')
    mode_adj = Decimal('1.0000')
    rationale = []

    if risk_assessment.risk_level == RiskLevel.BLOCKED:
        adjusted = Decimal('0.0000')
        sizing_mode = RiskSizingMode.CAPPED
        rationale.append('Risk level BLOCKED -> quantity forced to zero.')
    else:
        score = Decimal(str(risk_assessment.risk_score or '0'))
        confidence_adj = Decimal('0.50') if score < Decimal('40') else Decimal('0.70') if score < Decimal('60') else Decimal('0.90')

        if risk_assessment.liquidity_risk >= Decimal('14.00'):
            liquidity_adj = Decimal('0.60')
            rationale.append('Liquidity risk elevated, sizing reduced 40%.')
        elif risk_assessment.liquidity_risk >= Decimal('8.00'):
            liquidity_adj = Decimal('0.80')
            rationale.append('Liquidity risk moderate, sizing reduced 20%.')

        status = risk_assessment.safety_context.get('status', 'HEALTHY')
        if status in {'WARNING', 'COOLDOWN'}:
            safety_adj = Decimal('0.70')
            rationale.append(f'Safety status {status}, additional conservative reduction.')

        runtime_mode = risk_assessment.metadata.get('runtime_mode')
        if runtime_mode == 'OBSERVE_ONLY':
            mode_adj = Decimal('0.55')
            rationale.append('Runtime observe-only mode: use minimal sizing.')
        elif runtime_mode == 'PAPER_ASSIST':
            mode_adj = Decimal('0.75')

        adjusted = base_quantity * confidence_adj * liquidity_adj * safety_adj * mode_adj
        max_exposure_allowed = Decimal('350.00')
        reserve_cash = Decimal('250.00')
        reference_price = Decimal(str(risk_assessment.metadata.get('reference_price') or '1'))
        current_value = adjusted * reference_price
        if current_value > max_exposure_allowed:
            adjusted = max_exposure_allowed / reference_price
            rationale.append('Market exposure cap applied.')
            sizing_mode = RiskSizingMode.CAPPED
        else:
            sizing_mode = RiskSizingMode.HEURISTIC

        account_available = account.cash_balance - reserve_cash
        if account_available <= Decimal('0.00'):
            adjusted = Decimal('0.0000')
            rationale.append('Reserve cash constraint prevents additional sizing.')
            sizing_mode = RiskSizingMode.CAPPED
        elif (adjusted * reference_price) > account_available:
            adjusted = account_available / reference_price
            rationale.append('Reduced by portfolio cash reserve constraint.')
            sizing_mode = RiskSizingMode.CAPPED

    adjusted = _q4(max(Decimal('0.0000'), adjusted))
    return RiskSizingDecision.objects.create(
        risk_assessment=risk_assessment,
        base_quantity=_q4(base_quantity),
        adjusted_quantity=adjusted,
        sizing_mode=sizing_mode,
        sizing_rationale=' '.join(rationale) or 'Conservative default heuristic sizing.',
        max_exposure_allowed=Decimal('350.00'),
        reserve_cash_considered=Decimal('250.00'),
        confidence_adjustment=confidence_adj,
        liquidity_adjustment=liquidity_adj,
        safety_adjustment=safety_adj,
        metadata={**metadata, 'paper_demo_only': True},
    )

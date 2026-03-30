from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from apps.paper_trading.services.portfolio import get_active_account
from apps.risk_agent.models import (
    RiskApprovalDecision,
    RiskRuntimeApprovalStatus,
    RiskRuntimeCandidate,
    RiskRuntimeSizingMode,
    RiskSizingPlan,
)


def _q6(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)


def build_sizing_plan(*, candidate: RiskRuntimeCandidate, approval_decision: RiskApprovalDecision) -> RiskSizingPlan:
    cap_reason_codes: list[str] = []

    if approval_decision.approval_status == RiskRuntimeApprovalStatus.BLOCKED:
        return RiskSizingPlan.objects.create(
            linked_candidate=candidate,
            linked_approval_decision=approval_decision,
            sizing_mode=RiskRuntimeSizingMode.NO_TRADE,
            raw_size_fraction=Decimal('0.000000'),
            adjusted_size_fraction=Decimal('0.000000'),
            cap_applied=True,
            cap_reason_codes=['BLOCKED'],
            paper_notional_size=Decimal('0.00'),
            sizing_rationale='Blocked candidate: no paper trade sizing allowed.',
            metadata={'paper_demo_only': True, 'manual_first': True},
        )

    confidence = Decimal(str(candidate.confidence_score or '0'))
    uncertainty = Decimal(str(candidate.uncertainty_score or '0'))
    edge = Decimal(str(candidate.adjusted_edge or '0'))

    # Conservative bounded Kelly proxy (binary market, b=1), then fractionalize and cap.
    raw_kelly = max(Decimal('0.000000'), (Decimal('2.0') * edge))
    raw_kelly = min(raw_kelly, Decimal('0.120000'))

    if approval_decision.approval_status == RiskRuntimeApprovalStatus.APPROVED_REDUCED:
        sizing_mode = RiskRuntimeSizingMode.CAPPED_FRACTIONAL_KELLY
        base_fraction = raw_kelly * Decimal('0.33')
    else:
        sizing_mode = RiskRuntimeSizingMode.BOUNDED_KELLY
        base_fraction = raw_kelly * Decimal('0.50')

    quality_multiplier = max(Decimal('0.25'), min(Decimal('1.00'), confidence + (Decimal('0.50') - uncertainty)))
    adjusted_fraction = base_fraction * quality_multiplier

    if uncertainty > Decimal('0.60'):
        adjusted_fraction *= Decimal('0.60')
        cap_reason_codes.append('HIGH_UNCERTAINTY_CAP')
    if confidence < Decimal('0.55'):
        adjusted_fraction *= Decimal('0.70')
        cap_reason_codes.append('LOW_CONFIDENCE_CAP')
    if (candidate.market_liquidity_context or {}).get('bucket') in {'poor', 'thin'}:
        adjusted_fraction *= Decimal('0.60')
        cap_reason_codes.append('LIQUIDITY_CAP')

    portfolio = get_active_account()
    paper_risk_budget = Decimal('5000.00')
    max_exposure = Decimal(str(approval_decision.max_allowed_exposure or '0'))
    target_notional = adjusted_fraction * paper_risk_budget

    cap_applied = False
    if max_exposure > Decimal('0') and target_notional > max_exposure:
        target_notional = max_exposure
        adjusted_fraction = target_notional / paper_risk_budget
        cap_applied = True
        cap_reason_codes.append('APPROVAL_EXPOSURE_CAP')

    available = max(Decimal('0.00'), portfolio.cash_balance - Decimal('250.00'))
    if target_notional > available:
        target_notional = available
        adjusted_fraction = target_notional / paper_risk_budget if paper_risk_budget else Decimal('0')
        cap_applied = True
        cap_reason_codes.append('CASH_RESERVE_CAP')

    adjusted_fraction = _q6(max(Decimal('0.000000'), adjusted_fraction))
    return RiskSizingPlan.objects.create(
        linked_candidate=candidate,
        linked_approval_decision=approval_decision,
        sizing_mode=sizing_mode,
        raw_size_fraction=_q6(raw_kelly),
        adjusted_size_fraction=adjusted_fraction,
        cap_applied=cap_applied or bool(cap_reason_codes),
        cap_reason_codes=cap_reason_codes,
        paper_notional_size=target_notional.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        sizing_rationale=(
            f'raw_kelly={raw_kelly} edge={edge}, quality_multiplier={quality_multiplier}, '
            f'adjusted_fraction={adjusted_fraction}, risk_budget={paper_risk_budget}.'
        ),
        metadata={'paper_demo_only': True, 'no_real_money': True},
    )

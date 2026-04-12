from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.paper_trading.services.portfolio import build_account_financial_summary, get_active_account
from apps.prediction_agent.models import RiskReadyPredictionHandoff, RiskReadyPredictionHandoffStatus
from apps.risk_agent.models import RiskIntakeStatus, RiskRuntimeCandidate, RiskRuntimeRun


@dataclass
class IntakeBuildResult:
    candidates: list[RiskRuntimeCandidate]
    considered_count: int
    skipped_count: int


def _liquidity_bucket(liquidity_value: float) -> str:
    if liquidity_value < 10000:
        return 'poor'
    if liquidity_value < 40000:
        return 'thin'
    return 'good'


def _portfolio_pressure_state() -> tuple[str, dict[str, object]]:
    account = get_active_account()
    portfolio = build_account_financial_summary(account=account)
    cash_value = Decimal(str(portfolio.get('cash') or '0'))
    equity_value = Decimal(str(portfolio.get('equity') or '0'))
    exposure = cash_value + equity_value
    used = equity_value
    utilization = (used / exposure) if exposure > Decimal('0') else Decimal('0')
    context = {
        'equity_value': str(equity_value),
        'cash_balance': str(cash_value),
        'utilization': str(utilization),
        'account_summary_status': str(portfolio.get('summary_status') or ''),
        'account_summary_reason_codes': list(portfolio.get('reason_codes') or []),
    }
    if utilization >= Decimal('0.70'):
        return 'HIGH', context
    if utilization >= Decimal('0.45'):
        return 'MEDIUM', context
    return 'LOW', context


def build_runtime_candidates(*, runtime_run: RiskRuntimeRun) -> IntakeBuildResult:
    handoffs = (
        RiskReadyPredictionHandoff.objects.select_related(
            'linked_market',
            'linked_market__provider',
            'linked_conviction_review',
            'linked_conviction_review__linked_intake_candidate',
        )
        .order_by('-created_at', '-id')[:150]
    )

    candidates: list[RiskRuntimeCandidate] = []
    skipped = 0
    pressure_state, portfolio_context = _portfolio_pressure_state()

    for handoff in handoffs:
        market = handoff.linked_market
        review = handoff.linked_conviction_review
        intake_candidate = review.linked_intake_candidate if review else None
        if market is None or review is None:
            skipped += 1
            continue

        now = timezone.now()
        ttl_hours = None
        if market.close_time:
            delta = market.close_time - now
            ttl_hours = int(delta.total_seconds() // 3600) if delta > timedelta(0) else 0

        liquidity = float(market.liquidity or 0)
        volume = float(market.volume_24h or 0)
        spread_bps = int(market.spread_bps or 0)

        intake_status = RiskIntakeStatus.READY_FOR_RISK_RUNTIME
        reason_codes: list[str] = list(handoff.handoff_reason_codes or [])
        if handoff.handoff_status == RiskReadyPredictionHandoffStatus.BLOCKED:
            intake_status = RiskIntakeStatus.BLOCKED
            reason_codes.append('PREDICTION_HANDOFF_BLOCKED')
        elif handoff.handoff_status == RiskReadyPredictionHandoffStatus.DEFERRED:
            intake_status = RiskIntakeStatus.INSUFFICIENT_CONTEXT
            reason_codes.append('PREDICTION_HANDOFF_DEFERRED')
        elif handoff.handoff_status == RiskReadyPredictionHandoffStatus.WATCH:
            intake_status = RiskIntakeStatus.REDUCED_CONTEXT
            reason_codes.append('PREDICTION_HANDOFF_WATCH')

        if pressure_state == 'HIGH' and intake_status == RiskIntakeStatus.READY_FOR_RISK_RUNTIME:
            intake_status = RiskIntakeStatus.REDUCED_CONTEXT
            reason_codes.append('PORTFOLIO_PRESSURE_HIGH')

        context_summary = (
            f'handoff={handoff.handoff_status}, conviction={review.conviction_bucket}, '
            f'confidence={review.confidence}, uncertainty={review.uncertainty}, '
            f'portfolio_pressure={pressure_state}.'
        )

        candidates.append(
            RiskRuntimeCandidate.objects.create(
                runtime_run=runtime_run,
                linked_prediction_assessment=None,
                linked_risk_ready_prediction_handoff=handoff,
                linked_prediction_conviction_review=review,
                linked_prediction_intake_candidate=intake_candidate,
                linked_market=market,
                market_provider=market.provider.slug,
                category=market.category or (intake_candidate.category if intake_candidate else ''),
                intake_status=intake_status,
                calibrated_probability=review.calibrated_probability,
                market_probability=review.market_probability,
                adjusted_edge=review.adjusted_edge,
                confidence_score=review.confidence,
                uncertainty_score=review.uncertainty,
                conviction_bucket=review.conviction_bucket,
                portfolio_pressure_state=pressure_state,
                context_summary=context_summary,
                reason_codes=reason_codes,
                evidence_quality_score=Decimal('0.7000'),
                precedent_caution_score=Decimal(str((review.metadata or {}).get('precedent_caution_score', '0.3000'))),
                linked_portfolio_context=portfolio_context,
                linked_feedback_context=(review.metadata or {}).get('feedback_context', {}),
                market_liquidity_context={
                    'bucket': _liquidity_bucket(liquidity),
                    'liquidity': liquidity,
                    'volume_24h': volume,
                    'spread_bps': spread_bps,
                },
                time_to_resolution=ttl_hours,
                predicted_status=handoff.handoff_status,
                metadata={
                    'paper_demo_only': True,
                    'prediction_intake_run_id': intake_candidate.intake_run_id if intake_candidate else None,
                },
            )
        )

    return IntakeBuildResult(candidates=candidates, considered_count=handoffs.count(), skipped_count=skipped)

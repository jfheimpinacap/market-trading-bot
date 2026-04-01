from __future__ import annotations

from collections import Counter
from decimal import Decimal

from django.utils import timezone

from apps.autonomous_trader.models import AutonomousSizingDecision, AutonomousSizingDecisionStatus, AutonomousSizingRun, AutonomousTradeCandidate
from apps.autonomous_trader.services.kelly_sizing.adjustment import apply_conservative_adjustments
from apps.autonomous_trader.services.kelly_sizing.kelly import bounded_fractional_kelly
from apps.autonomous_trader.services.kelly_sizing.recommendation import emit_recommendations
from apps.autonomous_trader.services.kelly_sizing.sizing_context import build_sizing_context


def run_sizing_bridge(*, actor: str = 'operator-ui', cycle_run_id: int | None = None, limit: int = 25) -> dict:
    run = AutonomousSizingRun.objects.create(metadata={'actor': actor, 'cycle_run_id': cycle_run_id})
    candidates_qs = AutonomousTradeCandidate.objects.select_related('linked_market', 'cycle_run').order_by('-created_at', '-id')
    if cycle_run_id:
        candidates_qs = candidates_qs.filter(cycle_run_id=cycle_run_id)
    candidates = list(candidates_qs[:limit])

    recommendations = []
    decisions: list[AutonomousSizingDecision] = []
    for candidate in candidates:
        context = build_sizing_context(sizing_run=run, candidate=candidate)
        base_kelly, applied_fraction = bounded_fractional_kelly(
            edge=Decimal(candidate.adjusted_edge),
            confidence=Decimal(candidate.confidence),
            uncertainty=context.uncertainty,
        )
        notional_before = (Decimal('1000.00') * applied_fraction).quantize(Decimal('0.01'))
        notional_after, reason_codes, method = apply_conservative_adjustments(context=context, applied_fraction=applied_fraction)

        status = AutonomousSizingDecisionStatus.APPLIED
        if notional_after == Decimal('0.00'):
            status = AutonomousSizingDecisionStatus.BLOCKED
        elif reason_codes:
            status = AutonomousSizingDecisionStatus.REDUCED

        market_probability = context.market_probability or Decimal('0.50')
        price = max(Decimal('0.10'), min(Decimal('0.90'), Decimal(market_probability)))
        quantity = (notional_after / price).quantize(Decimal('0.0001')) if notional_after > 0 else Decimal('0.0000')

        decision = AutonomousSizingDecision.objects.create(
            linked_context=context,
            linked_candidate=candidate,
            sizing_method=method,
            decision_status=status,
            base_kelly_fraction=base_kelly,
            applied_fraction=applied_fraction,
            notional_before_adjustment=notional_before,
            notional_after_adjustment=notional_after,
            final_paper_quantity=quantity,
            adjustment_reason_codes=reason_codes,
            decision_summary=f'{method} status={status} reasons={reason_codes}',
            metadata={'paper_only': True, 'local_first': True},
        )
        decisions.append(decision)
        recommendations.extend(emit_recommendations(context=context, decision=decision))

    counter = Counter(r.recommendation_type for r in recommendations)
    run.considered_candidate_count = len(candidates)
    run.approved_for_sizing_count = sum(1 for d in decisions if d.decision_status in {'APPLIED', 'REDUCED'})
    run.reduced_by_portfolio_count = sum(1 for d in decisions if 'PORTFOLIO_CAP' in d.adjustment_reason_codes)
    run.reduced_by_risk_count = sum(1 for d in decisions if 'CONFIDENCE_DISCOUNT' in d.adjustment_reason_codes or 'UNCERTAINTY_DISCOUNT' in d.adjustment_reason_codes)
    run.blocked_for_sizing_count = sum(1 for d in decisions if d.decision_status == 'BLOCKED')
    run.sized_for_execution_count = sum(1 for d in decisions if (d.notional_after_adjustment or Decimal('0')) > 0)
    run.recommendation_summary = dict(counter)
    run.completed_at = timezone.now()
    run.save(update_fields=[
        'considered_candidate_count', 'approved_for_sizing_count', 'reduced_by_portfolio_count', 'reduced_by_risk_count',
        'blocked_for_sizing_count', 'sized_for_execution_count', 'recommendation_summary', 'completed_at', 'updated_at',
    ])
    return {'run': run, 'decisions': decisions, 'recommendations': recommendations}


def build_sizing_summary() -> dict:
    latest = AutonomousSizingRun.objects.order_by('-started_at', '-id').first()
    if not latest:
        return {
            'latest_run_id': None,
            'considered_candidate_count': 0,
            'approved_for_sizing_count': 0,
            'reduced_by_portfolio_count': 0,
            'reduced_by_risk_count': 0,
            'blocked_for_sizing_count': 0,
            'sized_for_execution_count': 0,
            'recommendation_summary': {},
        }
    return {
        'latest_run_id': latest.id,
        'considered_candidate_count': latest.considered_candidate_count,
        'approved_for_sizing_count': latest.approved_for_sizing_count,
        'reduced_by_portfolio_count': latest.reduced_by_portfolio_count,
        'reduced_by_risk_count': latest.reduced_by_risk_count,
        'blocked_for_sizing_count': latest.blocked_for_sizing_count,
        'sized_for_execution_count': latest.sized_for_execution_count,
        'recommendation_summary': latest.recommendation_summary,
    }

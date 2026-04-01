from __future__ import annotations

from decimal import Decimal

from apps.autonomous_trader.models import AutonomousSizingContext, AutonomousSizingDecision, AutonomousSizingRecommendation


def emit_recommendations(*, context: AutonomousSizingContext, decision: AutonomousSizingDecision) -> list[AutonomousSizingRecommendation]:
    created: list[AutonomousSizingRecommendation] = []
    if decision.decision_status == 'BLOCKED':
        created.append(AutonomousSizingRecommendation.objects.create(
            recommendation_type='BLOCK_SIZE_FOR_RISK_POSTURE',
            target_candidate=context.linked_candidate,
            target_context=context,
            target_sizing_decision=decision,
            rationale='Risk posture blocks sizing for this paper candidate.',
            reason_codes=['RISK_BLOCK'],
            confidence=Decimal('0.9200'),
            blockers=['RISK_POSTURE_BLOCKED'],
        ))
    elif decision.sizing_method == 'FIXED_NOTIONAL':
        created.append(AutonomousSizingRecommendation.objects.create(
            recommendation_type='USE_MINIMAL_FIXED_NOTIONAL',
            target_candidate=context.linked_candidate,
            target_context=context,
            target_sizing_decision=decision,
            rationale='Fallback to minimal fixed notional due to context sufficiency constraints.',
            reason_codes=decision.adjustment_reason_codes,
            confidence=Decimal('0.7400'),
            blockers=[],
        ))
    else:
        created.append(AutonomousSizingRecommendation.objects.create(
            recommendation_type='APPLY_CAPPED_FRACTIONAL_KELLY',
            target_candidate=context.linked_candidate,
            target_context=context,
            target_sizing_decision=decision,
            rationale='Apply bounded Kelly-informed paper sizing under risk and portfolio caps.',
            reason_codes=decision.adjustment_reason_codes,
            confidence=Decimal('0.8100'),
            blockers=[],
        ))

    if 'CONFIDENCE_DISCOUNT' in decision.adjustment_reason_codes:
        created.append(AutonomousSizingRecommendation.objects.create(
            recommendation_type='REDUCE_SIZE_FOR_LOW_CONFIDENCE',
            target_candidate=context.linked_candidate,
            target_context=context,
            target_sizing_decision=decision,
            rationale='Low confidence triggered conservative size discount.',
            reason_codes=['CONFIDENCE_DISCOUNT'],
            confidence=Decimal('0.8300'),
            blockers=[],
        ))
    if 'PORTFOLIO_CAP' in decision.adjustment_reason_codes or 'PORTFOLIO_BLOCK_NEW_ENTRIES' in decision.adjustment_reason_codes:
        created.append(AutonomousSizingRecommendation.objects.create(
            recommendation_type='REDUCE_SIZE_FOR_PORTFOLIO_PRESSURE',
            target_candidate=context.linked_candidate,
            target_context=context,
            target_sizing_decision=decision,
            rationale='Portfolio governor posture throttled this execution budget.',
            reason_codes=['PORTFOLIO_PRESSURE'],
            confidence=Decimal('0.8500'),
            blockers=['PORTFOLIO_POSTURE_CONSTRAINT'],
        ))
    return created

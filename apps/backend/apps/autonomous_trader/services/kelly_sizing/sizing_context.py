from __future__ import annotations

from decimal import Decimal

from apps.allocation_engine.models import AllocationDecision
from apps.autonomous_trader.models import (
    AutonomousCandidateStatus,
    AutonomousFeedbackInfluenceRecord,
    AutonomousSizingContext,
    AutonomousSizingContextStatus,
    AutonomousSizingRun,
    AutonomousTradeCandidate,
)
from apps.portfolio_governor.models import PortfolioExposureSnapshot, PortfolioThrottleDecision
from apps.prediction_agent.models import PredictionRuntimeRecommendation
from apps.risk_agent.models import RiskRuntimeRecommendation


def build_sizing_context(*, sizing_run: AutonomousSizingRun, candidate: AutonomousTradeCandidate) -> AutonomousSizingContext:
    latest_prediction = PredictionRuntimeRecommendation.objects.filter(target_assessment_id=candidate.metadata.get('prediction_assessment_id')).order_by('-created_at', '-id').first()
    latest_risk = RiskRuntimeRecommendation.objects.filter(target_candidate_id=candidate.metadata.get('risk_runtime_candidate_id')).order_by('-created_at', '-id').first()
    portfolio_snapshot = PortfolioExposureSnapshot.objects.order_by('-created_at_snapshot', '-id').first()
    portfolio_decision = PortfolioThrottleDecision.objects.order_by('-created_at_decision', '-id').first()
    feedback = AutonomousFeedbackInfluenceRecord.objects.filter(linked_candidate=candidate).order_by('-created_at', '-id').first()
    allocation = AllocationDecision.objects.filter(proposal__market=candidate.linked_market).order_by('-created_at', '-id').first()

    uncertainty = None
    if latest_prediction and latest_prediction.metadata:
        uncertainty_val = latest_prediction.metadata.get('uncertainty')
        if uncertainty_val is not None:
            uncertainty = Decimal(str(uncertainty_val))

    status = AutonomousSizingContextStatus.READY
    if candidate.candidate_status == AutonomousCandidateStatus.BLOCKED or candidate.risk_posture == 'BLOCKED':
        status = AutonomousSizingContextStatus.BLOCKED
    elif candidate.system_probability is None or candidate.market_probability is None:
        status = AutonomousSizingContextStatus.INSUFFICIENT_CONTEXT
    elif candidate.confidence < Decimal('0.55'):
        status = AutonomousSizingContextStatus.REDUCED

    return AutonomousSizingContext.objects.create(
        linked_run=sizing_run,
        linked_cycle_run=candidate.cycle_run,
        linked_candidate=candidate,
        linked_prediction_recommendation=latest_prediction,
        linked_risk_recommendation=latest_risk,
        linked_portfolio_snapshot=portfolio_snapshot,
        linked_feedback_influence=feedback,
        linked_allocation_context=allocation,
        system_probability=candidate.system_probability,
        market_probability=candidate.market_probability,
        adjusted_edge=candidate.adjusted_edge,
        confidence=candidate.confidence,
        uncertainty=uncertainty,
        risk_posture=candidate.risk_posture,
        portfolio_posture=portfolio_decision.state if portfolio_decision else 'UNKNOWN',
        context_status=status,
        context_summary=f'candidate={candidate.id} status={status} risk={candidate.risk_posture} portfolio={portfolio_decision.state if portfolio_decision else "UNKNOWN"}',
        metadata={'portfolio_throttle_decision_id': portfolio_decision.id if portfolio_decision else None},
    )

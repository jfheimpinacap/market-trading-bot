from __future__ import annotations

from decimal import Decimal

from apps.opportunity_supervisor.models import OpportunityFusionAssessment, OpportunityFusionCandidate, OpportunityFusionStatus
from apps.opportunity_supervisor.services.portfolio_context import build_portfolio_fit


def _clamp(value: Decimal) -> Decimal:
    return max(Decimal('0.0000'), min(Decimal('1.0000'), value.quantize(Decimal('0.0001'))))


def assess_candidate(*, candidate: OpportunityFusionCandidate) -> OpportunityFusionAssessment:
    confidence = Decimal(str(candidate.confidence_score or 0))
    edge = abs(Decimal(str(candidate.adjusted_edge or 0)))
    quality = Decimal(str(candidate.opportunity_quality_score or 0))
    learning_drag = _clamp(sum((Decimal(str(item.get('adjustment_strength', '0'))) for item in candidate.linked_learning_adjustments), Decimal('0.0000')))
    conviction = _clamp((confidence * Decimal('0.45')) + (edge * Decimal('2.2')) + (quality * Decimal('0.35')) - (learning_drag * Decimal('0.4')))

    risk_status = candidate.linked_risk_approval.approval_status if candidate.linked_risk_approval_id else None
    risk_score = Decimal(str(candidate.risk_score or '0.5000')) if candidate.risk_score is not None else Decimal('0.5000')
    execution_feasibility = _clamp((risk_score * Decimal('0.7')) + (Decimal('0.3') if candidate.linked_risk_sizing_plan_id else Decimal('0.0')))

    portfolio_fit, portfolio_meta = build_portfolio_fit(provider=candidate.provider, category=candidate.category)
    final_score = _clamp((conviction * Decimal('0.45')) + (execution_feasibility * Decimal('0.30')) + (portfolio_fit * Decimal('0.25')) - (learning_drag * Decimal('0.25')))

    reason_codes = []
    blockers = []
    if risk_status == 'BLOCKED':
        status = OpportunityFusionStatus.BLOCKED_BY_RISK
        reason_codes.append('risk_blocked')
        blockers.append('risk_approval_blocked')
    elif learning_drag >= Decimal('0.4500'):
        status = OpportunityFusionStatus.BLOCKED_BY_LEARNING
        reason_codes.append('learning_drag_high')
        blockers.append('active_learning_caution')
    elif conviction < Decimal('0.3500'):
        status = OpportunityFusionStatus.LOW_CONVICTION
        reason_codes.append('conviction_low')
    elif final_score >= Decimal('0.6500') and execution_feasibility >= Decimal('0.5500'):
        status = OpportunityFusionStatus.READY_FOR_PROPOSAL
        reason_codes.append('proposal_ready')
    elif final_score >= Decimal('0.4500'):
        status = OpportunityFusionStatus.WATCH_ONLY
        reason_codes.append('watch_only')
    else:
        status = OpportunityFusionStatus.NEEDS_REVIEW
        reason_codes.append('manual_review_required')

    return OpportunityFusionAssessment.objects.create(
        runtime_run=candidate.runtime_run,
        linked_candidate=candidate,
        fusion_status=status,
        conviction_score=conviction,
        execution_feasibility_score=execution_feasibility,
        learning_drag_score=learning_drag,
        portfolio_fit_score=portfolio_fit,
        final_opportunity_score=final_score,
        rationale=(
            f'conviction={conviction:.4f}, execution_feasibility={execution_feasibility:.4f}, '
            f'learning_drag={learning_drag:.4f}, portfolio_fit={portfolio_fit:.4f}, risk_status={risk_status or "none"}.'
        ),
        reason_codes=reason_codes,
        blockers=blockers,
        metadata={'portfolio': portfolio_meta, 'manual_first': True, 'paper_only': True},
    )

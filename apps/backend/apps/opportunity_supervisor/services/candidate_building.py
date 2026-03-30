from __future__ import annotations

from decimal import Decimal

from apps.learning_memory.models import LoopAdjustmentStatus, PostmortemLearningAdjustment
from apps.opportunity_supervisor.models import OpportunityCycleRuntimeRun, OpportunityFusionCandidate
from apps.prediction_agent.models import PredictionRuntimeAssessment
from apps.research_agent.models import MarketResearchCandidate
from apps.risk_agent.models import PositionWatchPlan, RiskApprovalDecision, RiskSizingPlan


def _latest_by_market(items, get_market_id):
    latest = {}
    for item in items.order_by('-created_at', '-id'):
        market_id = get_market_id(item)
        if market_id and market_id not in latest:
            latest[market_id] = item
    return latest


def build_fusion_candidates(*, runtime_run: OpportunityCycleRuntimeRun) -> list[OpportunityFusionCandidate]:
    research_by_market = _latest_by_market(
        MarketResearchCandidate.objects.select_related('linked_market').all(),
        lambda item: item.linked_market_id,
    )
    prediction_by_market = _latest_by_market(
        PredictionRuntimeAssessment.objects.select_related('linked_candidate', 'linked_candidate__linked_market').all(),
        lambda item: item.linked_candidate.linked_market_id if item.linked_candidate_id else None,
    )
    approval_by_market = _latest_by_market(
        RiskApprovalDecision.objects.select_related('linked_candidate', 'linked_candidate__linked_market').all(),
        lambda item: item.linked_candidate.linked_market_id if item.linked_candidate_id else None,
    )
    sizing_by_candidate = {
        item.linked_candidate_id: item
        for item in RiskSizingPlan.objects.select_related('linked_candidate').order_by('-created_at', '-id')
        if item.linked_candidate_id
    }
    watch_by_candidate = {
        item.linked_candidate_id: item
        for item in PositionWatchPlan.objects.select_related('linked_candidate').order_by('-created_at', '-id')
        if item.linked_candidate_id
    }

    active_adjustments = list(
        PostmortemLearningAdjustment.objects.filter(status=LoopAdjustmentStatus.ACTIVE)
        .order_by('-updated_at', '-id')[:200]
    )

    market_ids = set(research_by_market.keys()) | set(prediction_by_market.keys()) | set(approval_by_market.keys())
    candidates: list[OpportunityFusionCandidate] = []
    for market_id in sorted(market_ids):
        research = research_by_market.get(market_id)
        prediction = prediction_by_market.get(market_id)
        approval = approval_by_market.get(market_id)
        risk_candidate_id = approval.linked_candidate_id if approval else None
        sizing = sizing_by_candidate.get(risk_candidate_id)
        watch = watch_by_candidate.get(risk_candidate_id)

        linked_learning_adjustments = [
            {
                'id': adjustment.id,
                'adjustment_type': adjustment.adjustment_type,
                'scope': adjustment.scope,
                'scope_key': adjustment.scope_key,
                'adjustment_strength': str(adjustment.adjustment_strength),
                'reason_codes': adjustment.reason_codes,
            }
            for adjustment in active_adjustments
            if adjustment.scope == 'global'
            or (research and adjustment.scope == 'provider' and adjustment.scope_key == research.market_provider)
            or (research and adjustment.scope == 'category' and adjustment.scope_key == (research.category or ''))
        ]

        candidate = OpportunityFusionCandidate.objects.create(
            runtime_run=runtime_run,
            linked_market=(research.linked_market if research else (prediction.linked_candidate.linked_market if prediction else approval.linked_candidate.linked_market)),
            linked_research_candidate=research,
            linked_scan_signals=(research.linked_narrative_signals if research else []),
            linked_prediction_assessment=prediction,
            linked_risk_approval=approval,
            linked_risk_sizing_plan=sizing,
            linked_watch_plan=watch,
            linked_learning_adjustments=linked_learning_adjustments,
            provider=(research.market_provider if research else ''),
            category=(research.category if research else ''),
            market_probability=(prediction.market_probability if prediction else None),
            narrative_support_score=(research.narrative_support_score if research else Decimal('0.0000')),
            pursue_worthiness_score=(research.pursue_worthiness_score if research else Decimal('0.0000')),
            adjusted_edge=(prediction.adjusted_edge if prediction else Decimal('0.0000')),
            confidence_score=(prediction.confidence_score if prediction else Decimal('0.0000')),
            risk_score=(approval.risk_score if approval else None),
            opportunity_quality_score=(research.pursue_worthiness_score if research else Decimal('0.0000')),
            metadata={
                'paper_only': True,
                'manual_first': True,
                'prediction_status': prediction.prediction_status if prediction else None,
                'risk_approval_status': approval.approval_status if approval else None,
            },
        )
        candidates.append(candidate)

    return candidates

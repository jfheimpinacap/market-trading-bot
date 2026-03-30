from __future__ import annotations

from decimal import Decimal

from apps.opportunity_supervisor.models import OpportunityFusionAssessment, PaperOpportunityProposal, PaperOpportunityProposalStatus
from apps.proposal_engine.models import ProposalDirection
from apps.proposal_engine.services.proposal import generate_trade_proposal


def create_paper_proposal(*, assessment: OpportunityFusionAssessment) -> PaperOpportunityProposal:
    candidate = assessment.linked_candidate
    direction = ProposalDirection.BUY_YES if Decimal(str(candidate.market_probability or '0.5')) >= Decimal('0.5') else ProposalDirection.BUY_NO

    proposal = None
    proposal_status = PaperOpportunityProposalStatus.PROPOSED
    if assessment.fusion_status == 'READY_FOR_PROPOSAL':
        proposal = generate_trade_proposal(market=candidate.linked_market, triggered_from='opportunity_cycle_runtime')
        proposal_status = PaperOpportunityProposalStatus.READY
    elif assessment.fusion_status in {'WATCH_ONLY', 'LOW_CONVICTION'}:
        proposal_status = PaperOpportunityProposalStatus.WATCH
    elif assessment.fusion_status in {'BLOCKED_BY_RISK', 'BLOCKED_BY_LEARNING'}:
        proposal_status = PaperOpportunityProposalStatus.BLOCKED
    else:
        proposal_status = PaperOpportunityProposalStatus.SKIPPED

    sizing = candidate.linked_risk_sizing_plan
    watch_required = bool(candidate.linked_risk_approval.watch_required) if candidate.linked_risk_approval_id else False
    execution_sim_recommended = proposal_status == PaperOpportunityProposalStatus.READY and assessment.final_opportunity_score >= Decimal('0.7500')

    return PaperOpportunityProposal.objects.create(
        runtime_run=assessment.runtime_run,
        linked_assessment=assessment,
        proposal=proposal,
        proposal_status=proposal_status,
        recommended_direction=direction,
        calibrated_probability=(candidate.linked_prediction_assessment.calibrated_probability if candidate.linked_prediction_assessment_id else None),
        adjusted_edge=candidate.adjusted_edge,
        approved_size_fraction=(sizing.adjusted_size_fraction if sizing else None),
        paper_notional_size=(sizing.paper_notional_size if sizing else None),
        watch_required=watch_required,
        execution_sim_recommended=execution_sim_recommended,
        rationale=assessment.rationale,
        reason_codes=assessment.reason_codes,
        blockers=assessment.blockers,
        metadata={'proposal_engine_handoff': bool(proposal), 'manual_first': True, 'paper_only': True},
    )

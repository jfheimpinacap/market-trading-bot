from decimal import Decimal

from django.db import transaction

from apps.evaluation_lab.models import OutcomeAlignmentRecord, OutcomeAlignmentStatus, OutcomeResolution
from apps.markets.models import Market, MarketStatus
from apps.opportunity_supervisor.models import OpportunityFusionAssessment, PaperOpportunityProposal
from apps.prediction_agent.models import PredictionRuntimeAssessment
from apps.risk_agent.models import RiskApprovalDecision


def _parse_outcome(market: Market) -> str:
    raw = str((market.metadata or {}).get('resolved_outcome', 'unknown')).lower().strip()
    if raw in {OutcomeResolution.YES, OutcomeResolution.NO, OutcomeResolution.PARTIAL}:
        return raw
    return OutcomeResolution.UNKNOWN


def _realized_score(outcome: str) -> Decimal | None:
    mapping = {
        OutcomeResolution.YES: Decimal('1.0000'),
        OutcomeResolution.NO: Decimal('0.0000'),
        OutcomeResolution.PARTIAL: Decimal('0.5000'),
    }
    return mapping.get(outcome)


def _alignment_status(*, calibrated_probability: Decimal | None, adjusted_edge: Decimal | None, realized: Decimal | None, risk_status: str) -> str:
    if calibrated_probability is None or realized is None:
        return OutcomeAlignmentStatus.NEEDS_REVIEW

    if risk_status == 'BLOCKED':
        if realized <= Decimal('0.4000'):
            return OutcomeAlignmentStatus.GOOD_SKIP
        if realized >= Decimal('0.6000'):
            return OutcomeAlignmentStatus.BAD_SKIP

    if adjusted_edge is not None and adjusted_edge > 0 and realized < Decimal('0.5000'):
        return OutcomeAlignmentStatus.NO_EDGE_REALIZED
    if calibrated_probability >= Decimal('0.7000') and realized < Decimal('0.5000'):
        return OutcomeAlignmentStatus.OVERCONFIDENT
    if calibrated_probability <= Decimal('0.3000') and realized > Decimal('0.5000'):
        return OutcomeAlignmentStatus.UNDERCONFIDENT

    if abs(calibrated_probability - realized) <= Decimal('0.1500'):
        return OutcomeAlignmentStatus.WELL_CALIBRATED
    return OutcomeAlignmentStatus.NEEDS_REVIEW


def build_outcome_alignment_records(*, runtime_run) -> list[OutcomeAlignmentRecord]:
    records: list[OutcomeAlignmentRecord] = []
    resolved_markets = (
        Market.objects.filter(status=MarketStatus.RESOLVED)
        .select_related('provider')
        .order_by('-resolution_time', '-id')
    )

    with transaction.atomic():
        for market in resolved_markets:
            prediction = (
                PredictionRuntimeAssessment.objects.filter(linked_candidate__linked_market=market)
                .select_related('linked_candidate')
                .order_by('-created_at', '-id')
                .first()
            )
            risk = (
                RiskApprovalDecision.objects.filter(linked_candidate__linked_market=market)
                .select_related('linked_candidate')
                .order_by('-created_at', '-id')
                .first()
            )
            opportunity = (
                OpportunityFusionAssessment.objects.filter(linked_candidate__linked_market=market)
                .select_related('linked_candidate')
                .order_by('-created_at', '-id')
                .first()
            )
            proposal = (
                PaperOpportunityProposal.objects.filter(linked_assessment__linked_candidate__linked_market=market)
                .select_related('linked_assessment', 'linked_assessment__linked_candidate')
                .order_by('-created_at', '-id')
                .first()
            )

            resolved_outcome = _parse_outcome(market)
            realized = _realized_score(resolved_outcome)

            horizon_band = 'unknown'
            if market.resolution_time and prediction:
                days = (market.resolution_time - prediction.created_at).days
                if days <= 3:
                    horizon_band = '0-3d'
                elif days <= 14:
                    horizon_band = '4-14d'
                else:
                    horizon_band = '15d_plus'

            record = OutcomeAlignmentRecord.objects.create(
                run=runtime_run,
                linked_market=market,
                linked_prediction_assessment=prediction,
                linked_risk_approval=risk,
                linked_opportunity_assessment=opportunity,
                linked_paper_proposal=proposal,
                resolved_outcome=resolved_outcome,
                market_probability_at_decision=getattr(prediction, 'market_probability', None),
                system_probability_at_decision=getattr(prediction, 'system_probability', None),
                calibrated_probability_at_decision=getattr(prediction, 'calibrated_probability', None),
                adjusted_edge_at_decision=getattr(prediction, 'adjusted_edge', None),
                risk_status_at_decision=getattr(risk, 'approval_status', ''),
                proposal_status_at_decision=getattr(proposal, 'proposal_status', ''),
                realized_result_score=realized,
                alignment_status=_alignment_status(
                    calibrated_probability=getattr(prediction, 'calibrated_probability', None),
                    adjusted_edge=getattr(prediction, 'adjusted_edge', None),
                    realized=realized,
                    risk_status=getattr(risk, 'approval_status', ''),
                ),
                metadata={
                    'provider': market.provider.slug,
                    'category': market.category or 'uncategorized',
                    'model_mode': getattr(prediction, 'model_mode', 'unknown'),
                    'horizon_band': horizon_band,
                },
            )
            records.append(record)

    return records

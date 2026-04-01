from __future__ import annotations

from dataclasses import dataclass

from apps.autonomous_trader.models import AutonomousCandidateStatus, AutonomousTradeCandidate, AutonomousTradeCycleRun
from apps.opportunity_supervisor.models import OpportunityFusionCandidate


@dataclass
class IntakeResult:
    candidates: list[AutonomousTradeCandidate]


def consolidate_candidates(*, cycle_run: AutonomousTradeCycleRun, limit: int = 25) -> IntakeResult:
    upstream = OpportunityFusionCandidate.objects.select_related(
        'linked_market',
        'linked_research_candidate',
        'linked_prediction_assessment',
        'linked_risk_approval',
    ).order_by('-created_at', '-id')[:limit]

    created: list[AutonomousTradeCandidate] = []
    for row in upstream:
        risk_status = row.linked_risk_approval.approval_status if row.linked_risk_approval else ''
        status = AutonomousCandidateStatus.NEEDS_REVIEW
        if risk_status in {'APPROVED', 'APPROVED_REDUCED'} and row.adjusted_edge >= 0.05 and row.confidence_score >= 0.60:
            status = AutonomousCandidateStatus.EXECUTION_READY
        elif risk_status == 'BLOCKED':
            status = AutonomousCandidateStatus.BLOCKED
        elif row.adjusted_edge < 0.02 or row.confidence_score < 0.45:
            status = AutonomousCandidateStatus.LOW_CONVICTION
        else:
            status = AutonomousCandidateStatus.WATCH

        created.append(
            AutonomousTradeCandidate.objects.create(
                cycle_run=cycle_run,
                linked_market=row.linked_market,
                linked_research_candidate=row.linked_research_candidate,
                candidate_status=status,
                system_probability=row.linked_prediction_assessment.system_probability if row.linked_prediction_assessment else None,
                market_probability=row.market_probability,
                adjusted_edge=row.adjusted_edge,
                confidence=row.confidence_score,
                risk_posture=risk_status or 'UNKNOWN',
                metadata={
                    'source': 'opportunity_supervisor',
                    'opportunity_candidate_id': row.id,
                    'prediction_assessment_id': row.linked_prediction_assessment_id,
                    'risk_approval_id': row.linked_risk_approval_id,
                    'linked_scan_signals': row.linked_scan_signals,
                },
            )
        )
    return IntakeResult(candidates=created)

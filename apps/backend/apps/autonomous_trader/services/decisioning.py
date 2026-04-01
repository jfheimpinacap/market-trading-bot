from __future__ import annotations

from apps.autonomous_trader.models import (
    AutonomousCandidateStatus,
    AutonomousDecisionStatus,
    AutonomousDecisionType,
    AutonomousTradeCandidate,
    AutonomousTradeDecision,
)


def decide_candidate(*, candidate: AutonomousTradeCandidate) -> AutonomousTradeDecision:
    if candidate.candidate_status == AutonomousCandidateStatus.BLOCKED or candidate.risk_posture == 'BLOCKED':
        return AutonomousTradeDecision.objects.create(
            linked_candidate=candidate,
            decision_type=AutonomousDecisionType.BLOCK_BY_RISK,
            decision_status=AutonomousDecisionStatus.BLOCKED,
            rationale='Risk posture blocks this candidate from paper execution.',
            reason_codes=['RISK_BLOCK'],
        )

    if candidate.adjusted_edge < 0.02:
        return AutonomousTradeDecision.objects.create(
            linked_candidate=candidate,
            decision_type=AutonomousDecisionType.SKIP_LOW_EDGE,
            decision_status=AutonomousDecisionStatus.SKIPPED,
            rationale='Adjusted edge is below minimum autonomous threshold.',
            reason_codes=['LOW_EDGE'],
        )

    if candidate.confidence < 0.45:
        return AutonomousTradeDecision.objects.create(
            linked_candidate=candidate,
            decision_type=AutonomousDecisionType.SKIP_LOW_CONFIDENCE,
            decision_status=AutonomousDecisionStatus.SKIPPED,
            rationale='Confidence does not meet autonomous paper threshold.',
            reason_codes=['LOW_CONFIDENCE'],
        )

    if candidate.candidate_status == AutonomousCandidateStatus.EXECUTION_READY:
        return AutonomousTradeDecision.objects.create(
            linked_candidate=candidate,
            decision_type=AutonomousDecisionType.EXECUTE_PAPER_TRADE,
            decision_status=AutonomousDecisionStatus.PROPOSED,
            rationale='Prediction and risk context converge for autonomous paper execution.',
            reason_codes=['HIGH_CONVICTION', 'PAPER_ALLOWED'],
        )

    return AutonomousTradeDecision.objects.create(
        linked_candidate=candidate,
        decision_type=AutonomousDecisionType.KEEP_ON_WATCH,
        decision_status=AutonomousDecisionStatus.PROPOSED,
        rationale='Candidate retained for automated watch and reassessment.',
        reason_codes=['WATCH_CONTINUATION'],
    )

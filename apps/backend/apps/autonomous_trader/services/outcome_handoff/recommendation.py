from __future__ import annotations

from decimal import Decimal

from apps.autonomous_trader.models import AutonomousOutcomeHandoffRecommendation, AutonomousOutcomeHandoffRecommendationType


def create_recommendation(*, recommendation_type: str, rationale: str, reason_codes: list[str], confidence: Decimal, blockers: list[str], target_outcome=None, target_postmortem_handoff=None, target_learning_handoff=None, metadata=None):
    return AutonomousOutcomeHandoffRecommendation.objects.create(
        recommendation_type=recommendation_type,
        target_outcome=target_outcome,
        target_postmortem_handoff=target_postmortem_handoff,
        target_learning_handoff=target_learning_handoff,
        rationale=rationale,
        reason_codes=reason_codes,
        confidence=confidence,
        blockers=blockers,
        metadata=metadata or {},
    )


def recommend_wait_for_closure(*, outcome, blockers: list[str]):
    return create_recommendation(
        recommendation_type=AutonomousOutcomeHandoffRecommendationType.WAIT_FOR_OUTCOME_CLOSURE,
        target_outcome=outcome,
        rationale='Outcome is not closed yet; defer post-trade handoffs until closure.',
        reason_codes=['OUTCOME_NOT_CLOSED'],
        confidence=Decimal('0.9900'),
        blockers=blockers,
    )

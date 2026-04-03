from __future__ import annotations

from dataclasses import dataclass

from apps.mission_control.models import (
    GovernanceBacklogPressureDecision,
    GovernanceBacklogPressureRecommendationType,
)


@dataclass
class BacklogPressureRecommendationPayload:
    recommendation_type: str
    rationale: str
    confidence: float
    blockers: list[str]


def build_backlog_pressure_recommendation(*, decision: GovernanceBacklogPressureDecision) -> BacklogPressureRecommendationPayload:
    if decision.decision_type == 'SET_HIGH_PRESSURE':
        return BacklogPressureRecommendationPayload(
            recommendation_type=GovernanceBacklogPressureRecommendationType.LIMIT_NEW_ACTIVITY,
            rationale='Human governance backlog is high-pressure; limit new runtime activity until backlog recovers.',
            confidence=0.9,
            blockers=['GOVERNANCE_BACKLOG_HIGH'],
        )
    if decision.decision_type == 'SET_CAUTION_PRESSURE':
        return BacklogPressureRecommendationPayload(
            recommendation_type=GovernanceBacklogPressureRecommendationType.PREFER_REDUCED_CADENCE,
            rationale='Governance backlog is cautionary; prefer reduced cadence and keep operator awareness high.',
            confidence=0.82,
            blockers=['GOVERNANCE_BACKLOG_CAUTION'],
        )
    return BacklogPressureRecommendationPayload(
        recommendation_type=GovernanceBacklogPressureRecommendationType.KEEP_BASELINE,
        rationale='Governance backlog pressure is normal; keep baseline runtime cadence.',
        confidence=0.72,
        blockers=[],
    )

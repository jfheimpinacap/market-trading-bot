from __future__ import annotations

from apps.mission_control.models import (
    GovernanceBacklogPressureDecision,
    GovernanceBacklogPressureDecisionType,
    GovernanceBacklogPressureRecommendation,
    GovernanceBacklogPressureRecommendationType,
    GovernanceBacklogPressureSnapshot,
)


def build_backlog_pressure_recommendation(
    *,
    snapshot: GovernanceBacklogPressureSnapshot,
    decision: GovernanceBacklogPressureDecision,
) -> GovernanceBacklogPressureRecommendation:
    recommendation_type = GovernanceBacklogPressureRecommendationType.KEEP_BACKLOG_STABLE
    confidence = 0.65
    blockers: list[str] = []
    rationale = 'Backlog pressure is healthy and does not require runtime throttling from governance backlog load.'

    if decision.decision_type == GovernanceBacklogPressureDecisionType.ELEVATE_RUNTIME_CAUTION_SIGNAL:
        recommendation_type = GovernanceBacklogPressureRecommendationType.REDUCE_RUNTIME_INTENSITY_FOR_BACKLOG
        confidence = 0.73
        rationale = 'Backlog pressure is elevated by overdue/high-priority review load; reduce runtime intensity conservatively.'
    elif decision.decision_type == GovernanceBacklogPressureDecisionType.ELEVATE_MONITOR_ONLY_BIAS:
        recommendation_type = GovernanceBacklogPressureRecommendationType.INCREASE_MANUAL_REVIEW_URGENCY
        confidence = 0.79
        rationale = 'Backlog pressure is high with stacked overdue/blocked/follow-up signals; prioritize manual governance clearing urgency.'
    elif decision.decision_type == GovernanceBacklogPressureDecisionType.REQUIRE_MANUAL_BACKLOG_REVIEW:
        recommendation_type = GovernanceBacklogPressureRecommendationType.REQUIRE_BACKLOG_CLEARING
        confidence = 0.86
        blockers = ['manual_backlog_review_required', 'critical_governance_pressure']
        rationale = 'Critical backlog pressure requires manual review and backlog clearing before relaxing conservative runtime bias.'

    return GovernanceBacklogPressureRecommendation.objects.create(
        linked_pressure_snapshot=snapshot,
        linked_pressure_decision=decision,
        recommendation_type=recommendation_type,
        rationale=rationale,
        confidence=confidence,
        blockers=blockers,
    )

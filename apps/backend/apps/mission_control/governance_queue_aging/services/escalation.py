from __future__ import annotations

from dataclasses import dataclass

from apps.mission_control.models import (
    GovernanceQueueAgingRecommendationType,
    GovernanceQueueAgingStatus,
    GovernanceReviewItem,
    GovernanceReviewPriority,
)


@dataclass
class EscalationDecision:
    recommendation_type: str
    rationale: str
    confidence: float
    blockers: list[str]
    suggested_priority: str


PRIORITY_ORDER = [
    GovernanceReviewPriority.P1,
    GovernanceReviewPriority.P2,
    GovernanceReviewPriority.P3,
    GovernanceReviewPriority.P4,
]


def _promote_priority(current: str, target: str) -> str:
    current_index = PRIORITY_ORDER.index(current)
    target_index = PRIORITY_ORDER.index(target)
    return target if target_index < current_index else current


def build_escalation_decision(*, item: GovernanceReviewItem, aging_status: str) -> EscalationDecision:
    if aging_status == GovernanceQueueAgingStatus.STALE_BLOCKED:
        return EscalationDecision(
            recommendation_type=GovernanceQueueAgingRecommendationType.ESCALATE_BLOCKED_ITEM,
            rationale='Blocked item has remained stale and should be reviewed with elevated priority.',
            confidence=0.9,
            blockers=item.blockers,
            suggested_priority=_promote_priority(item.queue_priority, GovernanceReviewPriority.P1),
        )

    if aging_status == GovernanceQueueAgingStatus.FOLLOWUP_DUE:
        return EscalationDecision(
            recommendation_type=GovernanceQueueAgingRecommendationType.REQUIRE_FOLLOWUP_NOW,
            rationale='Required follow-up is overdue and should be performed immediately.',
            confidence=0.9,
            blockers=item.blockers,
            suggested_priority=_promote_priority(item.queue_priority, GovernanceReviewPriority.P2),
        )

    if aging_status == GovernanceQueueAgingStatus.MANUAL_REVIEW_OVERDUE:
        return EscalationDecision(
            recommendation_type=GovernanceQueueAgingRecommendationType.REQUIRE_OPERATOR_REVIEW_NOW,
            rationale='Manual review remains in-progress past policy threshold.',
            confidence=0.95,
            blockers=item.blockers,
            suggested_priority=_promote_priority(item.queue_priority, GovernanceReviewPriority.P1),
        )

    if aging_status == GovernanceQueueAgingStatus.PRIORITY_ESCALATION:
        target = GovernanceReviewPriority.P2 if item.queue_priority in {GovernanceReviewPriority.P3, GovernanceReviewPriority.P4} else GovernanceReviewPriority.P1
        return EscalationDecision(
            recommendation_type=(
                GovernanceQueueAgingRecommendationType.ESCALATE_TO_P2
                if target == GovernanceReviewPriority.P2
                else GovernanceQueueAgingRecommendationType.ESCALATE_TO_P1
            ),
            rationale='Open item age exceeds stale threshold and should be prioritized higher.',
            confidence=0.85,
            blockers=item.blockers,
            suggested_priority=_promote_priority(item.queue_priority, target),
        )

    return EscalationDecision(
        recommendation_type=GovernanceQueueAgingRecommendationType.KEEP_PRIORITY,
        rationale='Current priority is appropriate for item age and review status.',
        confidence=0.7,
        blockers=item.blockers,
        suggested_priority=item.queue_priority,
    )

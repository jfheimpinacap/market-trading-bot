from __future__ import annotations

from apps.mission_control.models import (
    GovernanceReviewItem,
    GovernanceReviewPriority,
    GovernanceReviewRecommendation,
    GovernanceReviewRecommendationType,
    GovernanceReviewSeverity,
)


def build_recommendation_for_item(item: GovernanceReviewItem) -> GovernanceReviewRecommendation:
    recommendation_type = GovernanceReviewRecommendationType.RETRY_LATER
    confidence = 0.6
    rationale = 'Reintentar en una siguiente pasada de gobernanza cuando cambie el contexto.'

    if item.queue_priority == GovernanceReviewPriority.P1 or item.severity == GovernanceReviewSeverity.CRITICAL:
        recommendation_type = GovernanceReviewRecommendationType.ESCALATE_PRIORITY
        confidence = 0.9
        rationale = 'Riesgo crítico detectado con bloqueadores activos; requiere escalado inmediato.'
    elif item.blockers:
        recommendation_type = GovernanceReviewRecommendationType.REVIEW_NOW
        confidence = 0.85
        rationale = 'El item mantiene bloqueadores activos y necesita revisión operativa prioritaria.'
    elif item.queue_priority == GovernanceReviewPriority.P4 and item.severity == GovernanceReviewSeverity.INFO:
        recommendation_type = GovernanceReviewRecommendationType.SAFE_TO_DISMISS
        confidence = 0.7
        rationale = 'Sin bloqueadores reales y con severidad baja; puede cerrarse como advisory-only.'
    elif 'MANUAL' in ' '.join(item.reason_codes).upper():
        recommendation_type = GovernanceReviewRecommendationType.REQUIRE_OPERATOR_CONFIRMATION
        confidence = 0.8
        rationale = 'Los reason codes exigen confirmación explícita de operador antes de avanzar.'

    return GovernanceReviewRecommendation.objects.create(
        linked_review_item=item,
        recommendation_type=recommendation_type,
        rationale=rationale,
        confidence=confidence,
        blockers=item.blockers,
    )

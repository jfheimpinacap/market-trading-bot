from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.champion_challenger.services.bindings import set_champion_binding
from apps.promotion_committee.models import PromotionDecisionLog, PromotionRecommendationCode, PromotionReviewRun


def apply_review_decision(*, review_run: PromotionReviewRun, actor: str, notes: str = '') -> PromotionReviewRun:
    if review_run.decision_mode != 'MANUAL_APPLY':
        raise ValidationError('Review run is recommendation-only; manual apply was not enabled.')

    if review_run.recommendation_code != PromotionRecommendationCode.PROMOTE_CHALLENGER:
        raise ValidationError('Manual apply currently supports only PROMOTE_CHALLENGER recommendations.')

    challenger = review_run.evidence_snapshot.challenger_binding
    if challenger is None:
        raise ValidationError('No challenger binding is attached to this review run.')

    set_champion_binding(binding=challenger)

    PromotionDecisionLog.objects.create(
        review_run=review_run,
        event_type='MANUAL_APPLY',
        actor=actor,
        notes=notes or 'Manual apply executed by operator.',
        payload={'applied_at': timezone.now().isoformat(), 'new_champion_binding_id': challenger.id},
    )
    return review_run

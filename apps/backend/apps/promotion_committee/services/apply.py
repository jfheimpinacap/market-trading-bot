from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.champion_challenger.services.bindings import set_champion_binding
from apps.promotion_committee.models import (
    AdoptionRollbackStatus,
    ManualAdoptionAction,
    ManualAdoptionActionStatus,
    PromotionCase,
    PromotionCaseStatus,
    PromotionDecisionLog,
    PromotionRecommendationCode,
    PromotionReviewRun,
)


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


def apply_manual_adoption_case(*, promotion_case: PromotionCase, actor: str, notes: str = '') -> ManualAdoptionAction:
    if promotion_case.case_status != PromotionCaseStatus.APPROVED_FOR_MANUAL_ADOPTION:
        raise ValidationError('Promotion case is not approved for manual adoption.')

    action = (
        ManualAdoptionAction.objects.filter(linked_promotion_case=promotion_case)
        .order_by('-created_at', '-id')
        .first()
    )
    if action is None:
        raise ValidationError('No adoption action exists for this case. Run adoption review first.')
    if action.action_status == ManualAdoptionActionStatus.BLOCKED:
        raise ValidationError('Adoption action is blocked and cannot be applied.')

    action.action_status = ManualAdoptionActionStatus.APPLIED
    action.applied_by = actor
    action.applied_at = timezone.now()
    action.metadata = {**(action.metadata or {}), 'notes': notes, 'manual_apply': True}
    action.save(update_fields=['action_status', 'applied_by', 'applied_at', 'metadata', 'updated_at'])

    if hasattr(action, 'rollback_plan'):
        rollback_plan = action.rollback_plan
        rollback_plan.rollback_status = AdoptionRollbackStatus.AVAILABLE
        rollback_plan.metadata = {**(rollback_plan.metadata or {}), 'available_after_apply': True}
        rollback_plan.save(update_fields=['rollback_status', 'metadata', 'updated_at'])

    return action

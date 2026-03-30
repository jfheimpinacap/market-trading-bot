from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.certification_board.models import (
    BaselineActivationCandidate,
    BaselineBindingType,
    PaperBaselineActivation,
    PaperBaselineActivationStatus,
    PaperBaselineConfirmation,
    PaperBaselineConfirmationStatus,
)
from apps.certification_board.services.active_registry import set_active_paper_binding
from apps.certification_board.services.rollback import prepare_activation_rollback


def get_or_create_paper_baseline_activation(*, candidate: BaselineActivationCandidate) -> PaperBaselineActivation:
    status = (
        PaperBaselineActivationStatus.READY_TO_ACTIVATE
        if candidate.ready_for_activation
        else PaperBaselineActivationStatus.BLOCKED
    )
    activation, _ = PaperBaselineActivation.objects.get_or_create(
        linked_confirmation=candidate.linked_paper_baseline_confirmation,
        linked_candidate=candidate,
        defaults={
            'activation_status': status,
            'target_component': candidate.target_component,
            'target_scope': candidate.target_scope,
            'previous_active_snapshot': {
                'reference': candidate.previous_active_reference,
            },
            'activated_snapshot': {
                'reference': candidate.proposed_active_reference,
            },
            'rationale': (
                'Activation candidate resolved and ready for explicit manual baseline activation.'
                if candidate.ready_for_activation
                else 'Activation candidate blocked pending binding re-check.'
            ),
            'reason_codes': ['READY_FOR_BASELINE_ACTIVATION'] if candidate.ready_for_activation else ['BINDING_RECHECK_REQUIRED'],
            'blockers': candidate.blockers,
            'metadata': candidate.metadata,
            'linked_binding_artifact': f'baseline_activation_candidate:{candidate.id}',
        },
    )
    return activation


@transaction.atomic
def activate_paper_baseline(*, confirmation_id: int, actor: str = 'operator-ui', rationale: str = '') -> PaperBaselineActivation:
    confirmation = PaperBaselineConfirmation.objects.select_related('linked_candidate').get(pk=confirmation_id)
    latest_candidate = BaselineActivationCandidate.objects.filter(
        linked_paper_baseline_confirmation=confirmation
    ).order_by('-created_at', '-id').first()

    if latest_candidate is None:
        raise ValueError('No baseline activation candidate exists. Run baseline activation review first.')

    activation = get_or_create_paper_baseline_activation(candidate=latest_candidate)
    if confirmation.confirmation_status != PaperBaselineConfirmationStatus.CONFIRMED:
        activation.activation_status = PaperBaselineActivationStatus.BLOCKED
        activation.blockers = ['baseline_confirmation_not_confirmed']
        activation.save(update_fields=['activation_status', 'blockers', 'updated_at'])
        return activation

    if not latest_candidate.ready_for_activation:
        activation.activation_status = PaperBaselineActivationStatus.BLOCKED
        activation.blockers = latest_candidate.blockers
        activation.save(update_fields=['activation_status', 'blockers', 'updated_at'])
        return activation

    activation.activation_status = PaperBaselineActivationStatus.ACTIVATED
    activation.activated_by = actor
    activation.activated_at = timezone.now()
    activation.rationale = rationale or 'Manual operator activated confirmed paper baseline and updated active binding registry.'
    activation.reason_codes = ['MANUAL_PAPER_BASELINE_ACTIVATION_APPLIED']
    activation.blockers = []
    activation.previous_active_snapshot = {
        **(activation.previous_active_snapshot or {}),
        'reference': latest_candidate.previous_active_reference,
    }
    activation.activated_snapshot = {
        **(confirmation.confirmed_baseline_snapshot or {}),
        'reference': latest_candidate.proposed_active_reference,
        'source_confirmation_id': confirmation.id,
    }
    activation.metadata = {**(activation.metadata or {}), 'manual_activation': True, 'auto_apply_performed': False}
    activation.save(
        update_fields=[
            'activation_status',
            'activated_by',
            'activated_at',
            'rationale',
            'reason_codes',
            'blockers',
            'previous_active_snapshot',
            'activated_snapshot',
            'metadata',
            'updated_at',
        ]
    )

    set_active_paper_binding(
        target_component=activation.target_component,
        target_scope=activation.target_scope,
        active_binding_type=BaselineBindingType.CHAMPION_REFERENCE,
        active_snapshot=activation.activated_snapshot,
        activation=activation,
        metadata={
            'source': 'paper_baseline_activation',
            'confirmation_id': confirmation.id,
        },
    )

    prepare_activation_rollback(activation=activation, actor=actor)
    return activation

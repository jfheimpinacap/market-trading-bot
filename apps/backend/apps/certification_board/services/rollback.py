from __future__ import annotations

from django.utils import timezone

from apps.certification_board.models import (
    ActivePaperBindingRecord,
    ActivePaperBindingStatus,
    BaselineBindingSnapshot,
    BaselineBindingStatus,
    BaselineBindingType,
    PaperBaselineActivation,
    PaperBaselineActivationStatus,
    PaperBaselineConfirmation,
    PaperBaselineConfirmationStatus,
)


def prepare_baseline_rollback(*, confirmation: PaperBaselineConfirmation, actor: str = 'operator-ui') -> PaperBaselineConfirmation:
    confirmation.confirmation_status = PaperBaselineConfirmationStatus.ROLLBACK_AVAILABLE
    confirmation.metadata = {**(confirmation.metadata or {}), 'rollback_ready': True, 'rollback_prepared_by': actor}
    confirmation.save(update_fields=['confirmation_status', 'metadata', 'updated_at'])

    BaselineBindingSnapshot.objects.create(
        linked_confirmation=confirmation,
        binding_type=BaselineBindingType.STACK_PROFILE_BINDING,
        binding_status=BaselineBindingStatus.REVERTED,
        binding_snapshot=confirmation.previous_baseline_snapshot,
        metadata={'actor': actor, 'operation': 'prepare_rollback'},
    )
    return confirmation


def prepare_activation_rollback(*, activation: PaperBaselineActivation, actor: str = 'operator-ui') -> PaperBaselineActivation:
    activation.metadata = {
        **(activation.metadata or {}),
        'rollback_ready': bool((activation.previous_active_snapshot or {}).get('reference')),
        'rollback_prepared_by': actor,
        'rollback_prepared_at': timezone.now().isoformat(),
    }
    activation.save(update_fields=['metadata', 'updated_at'])
    return activation


def rollback_baseline_activation(*, activation_id: int, actor: str = 'operator-ui') -> PaperBaselineActivation:
    activation = PaperBaselineActivation.objects.get(pk=activation_id)
    previous_snapshot = activation.previous_active_snapshot or {}
    previous_reference = previous_snapshot.get('reference')
    if not previous_reference:
        activation.activation_status = PaperBaselineActivationStatus.BLOCKED
        activation.blockers = ['missing_previous_active_snapshot_for_rollback']
        activation.save(update_fields=['activation_status', 'blockers', 'updated_at'])
        return activation

    ActivePaperBindingRecord.objects.filter(
        target_component=activation.target_component,
        target_scope=activation.target_scope,
        status=ActivePaperBindingStatus.ACTIVE,
    ).update(status=ActivePaperBindingStatus.REVERTED)

    ActivePaperBindingRecord.objects.create(
        target_component=activation.target_component,
        target_scope=activation.target_scope,
        active_binding_type=BaselineBindingType.CHAMPION_REFERENCE,
        active_snapshot=previous_snapshot,
        source_activation=activation,
        status=ActivePaperBindingStatus.ACTIVE,
        metadata={'operation': 'manual_activation_rollback', 'actor': actor},
    )

    activation.activation_status = PaperBaselineActivationStatus.ROLLBACK_AVAILABLE
    activation.metadata = {**(activation.metadata or {}), 'rollback_executed': True, 'rollback_actor': actor}
    activation.save(update_fields=['activation_status', 'metadata', 'updated_at'])
    return activation

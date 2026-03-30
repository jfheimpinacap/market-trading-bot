from __future__ import annotations

from apps.certification_board.models import (
    BaselineBindingSnapshot,
    BaselineBindingStatus,
    BaselineBindingType,
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

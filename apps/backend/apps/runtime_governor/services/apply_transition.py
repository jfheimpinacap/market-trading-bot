from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from apps.runtime_governor.mode_enforcement.services.run import run_mode_enforcement_review
from apps.runtime_governor.models import (
    RuntimeModeTransitionApplyRecord,
    RuntimeModeTransitionApplyStatus,
    RuntimeModeTransitionDecision,
    RuntimeModeTransitionDecisionType,
)
from apps.runtime_governor.services.operating_mode.mode_switch import (
    GLOBAL_MODE_METADATA_KEY,
    build_downstream_influence,
    get_active_global_operating_mode,
)
from apps.runtime_governor.services.state import get_runtime_state


BLOCKED_DECISION_TYPES = {
    RuntimeModeTransitionDecisionType.DEFER_MODE_SWITCH,
    RuntimeModeTransitionDecisionType.KEEP_CURRENT_MODE_FOR_DWELL,
    RuntimeModeTransitionDecisionType.BLOCK_MODE_SWITCH,
    RuntimeModeTransitionDecisionType.REQUIRE_MANUAL_STABILITY_REVIEW,
}


@dataclass
class TransitionApplyResult:
    apply_record: RuntimeModeTransitionApplyRecord
    enforcement_run_id: int | None = None


@transaction.atomic
def apply_stabilized_transition_decision(
    *,
    transition_decision: RuntimeModeTransitionDecision,
    triggered_by: str = 'runtime-page-manual',
    auto_apply_safe: bool = False,
) -> TransitionApplyResult:
    current_mode = get_active_global_operating_mode()
    target_mode = transition_decision.linked_transition_snapshot.target_mode

    metadata = {
        'triggered_by': triggered_by,
        'auto_apply_safe': auto_apply_safe,
        'decision_type': transition_decision.decision_type,
        'decision_status': transition_decision.decision_status,
    }

    if transition_decision.decision_type in BLOCKED_DECISION_TYPES:
        record = RuntimeModeTransitionApplyRecord.objects.create(
            linked_transition_decision=transition_decision,
            apply_status=RuntimeModeTransitionApplyStatus.BLOCKED,
            previous_mode=current_mode,
            applied_mode=None,
            enforcement_refreshed=False,
            apply_summary='Stabilized transition apply blocked by transition decision outcome.',
            metadata=metadata,
        )
        return TransitionApplyResult(apply_record=record)

    if transition_decision.decision_type != RuntimeModeTransitionDecisionType.ALLOW_MODE_SWITCH:
        record = RuntimeModeTransitionApplyRecord.objects.create(
            linked_transition_decision=transition_decision,
            apply_status=RuntimeModeTransitionApplyStatus.SKIPPED,
            previous_mode=current_mode,
            applied_mode=current_mode,
            enforcement_refreshed=False,
            apply_summary='Stabilized transition decision did not map to an executable mode switch.',
            metadata=metadata,
        )
        return TransitionApplyResult(apply_record=record)

    if target_mode == current_mode:
        record = RuntimeModeTransitionApplyRecord.objects.create(
            linked_transition_decision=transition_decision,
            apply_status=RuntimeModeTransitionApplyStatus.SKIPPED,
            previous_mode=current_mode,
            applied_mode=current_mode,
            enforcement_refreshed=False,
            apply_summary='No mode change required; target mode already active.',
            metadata={**metadata, 'mode_switched': False},
        )
        return TransitionApplyResult(apply_record=record)

    state = get_runtime_state()
    state_metadata = dict(state.metadata or {})
    state_metadata[GLOBAL_MODE_METADATA_KEY] = target_mode
    state_metadata['global_operating_mode_influence'] = build_downstream_influence(mode=target_mode)
    state_metadata['runtime_mode_stabilization_last_apply_record_id'] = None
    state.metadata = state_metadata
    state.save(update_fields=['metadata', 'updated_at'])

    enforcement_result = run_mode_enforcement_review(triggered_by='runtime-mode-transition-apply')
    enforcement_run_id = enforcement_result['run'].id

    apply_record = RuntimeModeTransitionApplyRecord.objects.create(
        linked_transition_decision=transition_decision,
        apply_status=RuntimeModeTransitionApplyStatus.APPLIED,
        previous_mode=current_mode,
        applied_mode=target_mode,
        enforcement_refreshed=True,
        apply_summary=f'Applied stabilized transition from {current_mode} to {target_mode}.',
        metadata={
            **metadata,
            'mode_switched': True,
            'enforcement_run_id': enforcement_run_id,
            'runtime_state_id': state.id,
        },
    )

    state_metadata['runtime_mode_stabilization_last_apply_record_id'] = apply_record.id
    state.metadata = state_metadata
    state.save(update_fields=['metadata', 'updated_at'])

    transition_decision.metadata = {
        **(transition_decision.metadata or {}),
        'last_apply_record_id': apply_record.id,
        'last_apply_triggered_by': triggered_by,
    }
    transition_decision.save(update_fields=['metadata', 'updated_at'])

    return TransitionApplyResult(apply_record=apply_record, enforcement_run_id=enforcement_run_id)

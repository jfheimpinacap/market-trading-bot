from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from apps.runtime_governor.mode_enforcement.services.run import run_mode_enforcement_review
from apps.runtime_governor.models import (
    RuntimeFeedbackApplyDecision,
    RuntimeFeedbackApplyRecord,
    RuntimeFeedbackApplyRecordStatus,
    RuntimeFeedbackApplyStatus,
    RuntimeFeedbackApplyType,
    RuntimeFeedbackDecision,
    RuntimeFeedbackDecisionType,
    SafetyPostureState,
)
from apps.runtime_governor.services.apply_transition import apply_stabilized_transition_decision
from apps.runtime_governor.services.stability_review import build_runtime_mode_stability_review
from apps.runtime_governor.services.transition_decision import build_runtime_mode_transition_decision
from apps.runtime_governor.services.transition_snapshot import build_runtime_mode_transition_snapshot
from apps.runtime_governor.services.operating_mode.mode_switch import (
    GLOBAL_MODE_METADATA_KEY,
    build_downstream_influence,
    get_active_global_operating_mode,
)
from apps.runtime_governor.services.state import get_runtime_state


DECISION_TO_APPLY_TYPE: dict[str, str] = {
    RuntimeFeedbackDecisionType.KEEP_CURRENT_GLOBAL_MODE: RuntimeFeedbackApplyType.APPLY_KEEP_CURRENT_MODE,
    RuntimeFeedbackDecisionType.SHIFT_TO_MORE_CONSERVATIVE_MODE: RuntimeFeedbackApplyType.APPLY_SHIFT_TO_CAUTION,
    RuntimeFeedbackDecisionType.SHIFT_TO_MONITOR_ONLY: RuntimeFeedbackApplyType.APPLY_SHIFT_TO_MONITOR_ONLY,
    RuntimeFeedbackDecisionType.ENTER_RECOVERY_MODE: RuntimeFeedbackApplyType.APPLY_ENTER_RECOVERY_MODE,
    RuntimeFeedbackDecisionType.RELAX_TO_CAUTION: RuntimeFeedbackApplyType.APPLY_RELAX_TO_CAUTION,
    RuntimeFeedbackDecisionType.REDUCE_ADMISSION_AND_CADENCE: RuntimeFeedbackApplyType.APPLY_SHIFT_TO_CAUTION,
    RuntimeFeedbackDecisionType.REQUIRE_MANUAL_RUNTIME_REVIEW: RuntimeFeedbackApplyType.APPLY_MANUAL_REVIEW_ONLY,
}

APPLY_TYPE_TO_MODE: dict[str, str | None] = {
    RuntimeFeedbackApplyType.APPLY_KEEP_CURRENT_MODE: None,
    RuntimeFeedbackApplyType.APPLY_SHIFT_TO_CAUTION: 'CAUTION',
    RuntimeFeedbackApplyType.APPLY_SHIFT_TO_MONITOR_ONLY: 'MONITOR_ONLY',
    RuntimeFeedbackApplyType.APPLY_ENTER_RECOVERY_MODE: 'RECOVERY_MODE',
    RuntimeFeedbackApplyType.APPLY_RELAX_TO_CAUTION: 'CAUTION',
    RuntimeFeedbackApplyType.APPLY_MANUAL_REVIEW_ONLY: None,
}


@dataclass
class ApplyExecutionResult:
    apply_decision: RuntimeFeedbackApplyDecision
    apply_record: RuntimeFeedbackApplyRecord


def build_apply_decision(*, feedback_decision: RuntimeFeedbackDecision, apply_run_id: int | None = None) -> RuntimeFeedbackApplyDecision:
    current_mode = get_active_global_operating_mode()
    apply_type = DECISION_TO_APPLY_TYPE.get(feedback_decision.decision_type, RuntimeFeedbackApplyType.APPLY_MANUAL_REVIEW_ONLY)
    target_mode = APPLY_TYPE_TO_MODE.get(apply_type)

    reason_codes = list(dict.fromkeys((feedback_decision.reason_codes or []) + [feedback_decision.decision_type.lower()]))
    auto_applicable = feedback_decision.auto_applicable and apply_type != RuntimeFeedbackApplyType.APPLY_MANUAL_REVIEW_ONLY
    summary = f'Apply review mapped {feedback_decision.decision_type} to {apply_type}.'

    if apply_type == RuntimeFeedbackApplyType.APPLY_KEEP_CURRENT_MODE:
        target_mode = current_mode
        summary = 'Feedback apply review keeps current global mode unchanged.'

    safety_posture = feedback_decision.linked_performance_snapshot.metadata.get('safety_posture')
    if safety_posture == SafetyPostureState.HARD_BLOCK and apply_type not in {
        RuntimeFeedbackApplyType.APPLY_KEEP_CURRENT_MODE,
        RuntimeFeedbackApplyType.APPLY_ENTER_RECOVERY_MODE,
    }:
        apply_type = RuntimeFeedbackApplyType.APPLY_MANUAL_REVIEW_ONLY
        target_mode = None
        auto_applicable = False
        reason_codes.append('safety_hard_block_conflict')
        summary = 'Safety hard block conflicts with requested adjustment; require manual review.'

    if current_mode == 'RECOVERY_MODE' and apply_type == RuntimeFeedbackApplyType.APPLY_SHIFT_TO_CAUTION:
        apply_type = RuntimeFeedbackApplyType.APPLY_MANUAL_REVIEW_ONLY
        target_mode = None
        auto_applicable = False
        reason_codes.append('recovery_hysteresis_block')
        summary = 'Recovery hysteresis blocks direct caution shift; manual review required.'

    return RuntimeFeedbackApplyDecision.objects.create(
        linked_feedback_decision=feedback_decision,
        linked_apply_run_id=apply_run_id,
        current_mode=current_mode,
        target_mode=target_mode,
        apply_type=apply_type,
        apply_status=RuntimeFeedbackApplyStatus.PROPOSED,
        auto_applicable=auto_applicable,
        apply_summary=summary,
        reason_codes=reason_codes,
        metadata={
            'linked_feedback_decision_status': feedback_decision.decision_status,
            'linked_feedback_decision_type': feedback_decision.decision_type,
        },
    )


@transaction.atomic
def apply_runtime_feedback_apply_decision(*, apply_decision: RuntimeFeedbackApplyDecision, triggered_by: str = 'runtime-feedback-apply-review') -> ApplyExecutionResult:
    current_mode = get_active_global_operating_mode()

    if apply_decision.apply_type == RuntimeFeedbackApplyType.APPLY_MANUAL_REVIEW_ONLY:
        apply_decision.apply_status = RuntimeFeedbackApplyStatus.BLOCKED
        apply_decision.save(update_fields=['apply_status', 'updated_at'])
        record = RuntimeFeedbackApplyRecord.objects.create(
            linked_apply_decision=apply_decision,
            record_status=RuntimeFeedbackApplyRecordStatus.BLOCKED,
            previous_mode=current_mode,
            applied_mode=None,
            enforcement_refreshed=False,
            record_summary='Apply decision blocked pending manual runtime feedback review.',
            metadata={'triggered_by': triggered_by},
        )
        return ApplyExecutionResult(apply_decision=apply_decision, apply_record=record)

    target_mode = apply_decision.target_mode or current_mode
    mode_switched = target_mode != current_mode

    if apply_decision.apply_type == RuntimeFeedbackApplyType.APPLY_KEEP_CURRENT_MODE:
        apply_decision.apply_status = RuntimeFeedbackApplyStatus.SKIPPED
        apply_decision.save(update_fields=['apply_status', 'updated_at'])
        record = RuntimeFeedbackApplyRecord.objects.create(
            linked_apply_decision=apply_decision,
            record_status=RuntimeFeedbackApplyRecordStatus.SKIPPED,
            previous_mode=current_mode,
            applied_mode=current_mode,
            enforcement_refreshed=False,
            record_summary='No global mode switch required; feedback kept as conservative advisory.',
            metadata={'triggered_by': triggered_by},
        )
        return ApplyExecutionResult(apply_decision=apply_decision, apply_record=record)

    stabilization_apply_record = None
    if mode_switched:
        transition_snapshot = build_runtime_mode_transition_snapshot(
            run_id=None,
            feedback_decision=apply_decision.linked_feedback_decision,
            target_mode=target_mode,
        )
        stability_review = build_runtime_mode_stability_review(transition_snapshot=transition_snapshot)
        transition_decision = build_runtime_mode_transition_decision(
            transition_snapshot=transition_snapshot,
            stability_review=stability_review,
        )
        stabilization_result = apply_stabilized_transition_decision(
            transition_decision=transition_decision,
            triggered_by=f'runtime-feedback-apply:{triggered_by}',
            auto_apply_safe=False,
        )
        stabilization_apply_record = stabilization_result.apply_record
        if stabilization_apply_record.apply_status != 'APPLIED':
            apply_decision.apply_status = RuntimeFeedbackApplyStatus.BLOCKED
            apply_decision.metadata = {
                **(apply_decision.metadata or {}),
                'stabilization_transition_decision_id': transition_decision.id,
                'stabilization_apply_record_id': stabilization_apply_record.id,
            }
            apply_decision.save(update_fields=['apply_status', 'metadata', 'updated_at'])
            record = RuntimeFeedbackApplyRecord.objects.create(
                linked_apply_decision=apply_decision,
                record_status=RuntimeFeedbackApplyRecordStatus.BLOCKED,
                previous_mode=current_mode,
                applied_mode=None,
                enforcement_refreshed=False,
                record_summary='Runtime feedback apply blocked by mode stabilization gate.',
                metadata={
                    'triggered_by': triggered_by,
                    'stabilization_transition_decision_id': transition_decision.id,
                    'stabilization_apply_record_id': stabilization_apply_record.id,
                },
            )
            return ApplyExecutionResult(apply_decision=apply_decision, apply_record=record)

    state = get_runtime_state()
    metadata = dict(state.metadata or {})
    metadata[GLOBAL_MODE_METADATA_KEY] = target_mode
    metadata['global_operating_mode_influence'] = build_downstream_influence(mode=target_mode)
    metadata['runtime_feedback_apply_last_decision_id'] = apply_decision.id
    state.metadata = metadata
    state.save(update_fields=['metadata', 'updated_at'])

    apply_decision.apply_status = RuntimeFeedbackApplyStatus.APPLIED
    apply_decision.metadata = {
        **(apply_decision.metadata or {}),
        'applied_to_runtime_state_id': state.id,
        'triggered_by': triggered_by,
    }
    apply_decision.save(update_fields=['apply_status', 'metadata', 'updated_at'])

    enforcement_refreshed = bool(stabilization_apply_record.enforcement_refreshed) if stabilization_apply_record else False
    enforcement_run_id = None
    if mode_switched and not stabilization_apply_record:
        enforcement_result = run_mode_enforcement_review(triggered_by='runtime-feedback-apply')
        enforcement_refreshed = True
        enforcement_run_id = enforcement_result['run'].id
    elif stabilization_apply_record:
        enforcement_run_id = stabilization_apply_record.metadata.get('enforcement_run_id')

    record = RuntimeFeedbackApplyRecord.objects.create(
        linked_apply_decision=apply_decision,
        record_status=RuntimeFeedbackApplyRecordStatus.APPLIED,
        previous_mode=current_mode,
        applied_mode=target_mode,
        enforcement_refreshed=enforcement_refreshed,
        record_summary=f'Applied runtime feedback with target mode {target_mode}.',
        metadata={
            'triggered_by': triggered_by,
            'mode_switched': mode_switched,
            'enforcement_run_id': enforcement_run_id,
            'stabilization_apply_record_id': stabilization_apply_record.id if stabilization_apply_record else None,
        },
    )
    return ApplyExecutionResult(apply_decision=apply_decision, apply_record=record)

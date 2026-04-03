from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from apps.runtime_governor.models import (
    GlobalOperatingMode,
    GlobalOperatingModeDecision,
    GlobalOperatingModeDecisionStatus,
    GlobalOperatingModeDecisionType,
    GlobalOperatingModeSwitchRecord,
    GlobalOperatingModeSwitchStatus,
    GlobalRuntimePostureSnapshot,
    RuntimeModeState,
)
from apps.runtime_governor.services.state import get_runtime_state
from apps.runtime_governor.tuning_profiles import get_runtime_conservative_tuning_profile

GLOBAL_MODE_METADATA_KEY = 'global_operating_mode'


@dataclass
class OperatingModeReviewResult:
    decision: GlobalOperatingModeDecision
    switch_record: GlobalOperatingModeSwitchRecord


def get_active_global_operating_mode() -> str:
    state = get_runtime_state()
    return (state.metadata or {}).get(GLOBAL_MODE_METADATA_KEY, GlobalOperatingMode.BALANCED)


def _with_hysteresis(*, current_mode: str, proposed_mode: str, snapshot: GlobalRuntimePostureSnapshot) -> str:
    tuning = get_runtime_conservative_tuning_profile()
    governance_backlog_pressure_state = str(
        ((snapshot.metadata or {}).get('linked_models') or {}).get('governance_backlog_pressure_state') or 'NORMAL'
    ).upper()
    if current_mode == GlobalOperatingMode.BLOCKED and proposed_mode != GlobalOperatingMode.BLOCKED:
        if snapshot.safety_posture == 'HARD_BLOCK' or snapshot.runtime_posture == 'BLOCKED':
            return GlobalOperatingMode.BLOCKED
    if current_mode == GlobalOperatingMode.THROTTLED and proposed_mode == GlobalOperatingMode.CAUTION:
        if governance_backlog_pressure_state in {'HIGH', 'CRITICAL'}:
            return GlobalOperatingMode.THROTTLED
    if current_mode == GlobalOperatingMode.RECOVERY_MODE and proposed_mode == GlobalOperatingMode.BALANCED:
        if snapshot.recent_loss_state != 'NONE' or governance_backlog_pressure_state in {'HIGH', 'CRITICAL'}:
            return GlobalOperatingMode.RECOVERY_MODE
    if current_mode in {GlobalOperatingMode.RECOVERY_MODE, GlobalOperatingMode.THROTTLED} and proposed_mode in {
        GlobalOperatingMode.CAUTION,
        GlobalOperatingMode.BALANCED,
        GlobalOperatingMode.MONITOR_ONLY,
    }:
        if governance_backlog_pressure_state == 'CRITICAL' and tuning.critical_backlog_blocks_relax:
            return current_mode
    return proposed_mode


def _derive_target_mode(snapshot: GlobalRuntimePostureSnapshot) -> tuple[str, str, bool, list[str]]:
    tuning = get_runtime_conservative_tuning_profile()
    reason_codes = list(snapshot.reason_codes or [])
    governance_backlog_pressure_state = str(
        ((snapshot.metadata or {}).get('linked_models') or {}).get('governance_backlog_pressure_state') or 'NORMAL'
    ).upper()
    if governance_backlog_pressure_state != 'NORMAL':
        reason_codes.append(f'governance_backlog_pressure:{governance_backlog_pressure_state}')
    if snapshot.safety_posture == 'HARD_BLOCK' or snapshot.runtime_posture == 'BLOCKED':
        return GlobalOperatingMode.BLOCKED, GlobalOperatingModeDecisionType.SWITCH_TO_BLOCKED, True, reason_codes

    if snapshot.recent_loss_state == 'REPEATED_LOSS':
        return GlobalOperatingMode.RECOVERY_MODE, GlobalOperatingModeDecisionType.SWITCH_TO_RECOVERY_MODE, True, reason_codes

    if snapshot.portfolio_pressure_state in {'THROTTLED', 'BLOCK_NEW_ENTRIES'} or snapshot.exposure_pressure_state in {'THROTTLED', 'BLOCK_NEW_ACTIVITY'}:
        return GlobalOperatingMode.THROTTLED, GlobalOperatingModeDecisionType.SWITCH_TO_THROTTLED, True, reason_codes

    if snapshot.signal_quality_state == 'QUIET':
        return GlobalOperatingMode.MONITOR_ONLY, GlobalOperatingModeDecisionType.SWITCH_TO_MONITOR_ONLY, True, reason_codes

    caution_flags = sum(
        1
        for state in [
            snapshot.admission_pressure_state,
            snapshot.exposure_pressure_state,
            snapshot.session_health_state,
            snapshot.incident_pressure_state,
            snapshot.portfolio_pressure_state,
            snapshot.runtime_posture,
            snapshot.safety_posture,
        ]
        if state in {'CAUTION', 'DEGRADED', 'HIGH'}
    )
    if caution_flags >= 2:
        return GlobalOperatingMode.CAUTION, GlobalOperatingModeDecisionType.SWITCH_TO_CAUTION, True, reason_codes

    if caution_flags == 1 and snapshot.signal_quality_state == 'WEAK':
        return GlobalOperatingMode.CAUTION, GlobalOperatingModeDecisionType.REQUIRE_MANUAL_MODE_REVIEW, False, reason_codes + ['ambiguous_context']

    if governance_backlog_pressure_state == 'CAUTION':
        return GlobalOperatingMode.CAUTION, GlobalOperatingModeDecisionType.SWITCH_TO_CAUTION, True, reason_codes + ['backlog_caution_bias']
    if governance_backlog_pressure_state == 'HIGH':
        if tuning.high_backlog_manual_review_bias:
            reason_codes.append('backlog_high_manual_review_bias')
        return (
            GlobalOperatingMode.THROTTLED,
            GlobalOperatingModeDecisionType.SWITCH_TO_THROTTLED,
            True,
            reason_codes + ['backlog_high_reduce_admission_and_cadence'],
        )
    if governance_backlog_pressure_state == 'CRITICAL':
        if tuning.critical_backlog_monitor_only_bias:
            reason_codes.append('backlog_critical_monitor_only_bias')
        return (
            GlobalOperatingMode.MONITOR_ONLY,
            GlobalOperatingModeDecisionType.REQUIRE_MANUAL_MODE_REVIEW,
            False,
            reason_codes + ['backlog_critical_manual_review_required'],
        )

    return GlobalOperatingMode.BALANCED, GlobalOperatingModeDecisionType.KEEP_CURRENT_MODE, True, reason_codes


def build_downstream_influence(*, mode: str) -> dict:
    influence = {
        'cadence': 'default',
        'admission': 'default',
        'exposure': 'default',
        'heartbeat': 'default',
        'execution_intake': 'default',
        'session_recovery': 'default',
    }
    if mode == GlobalOperatingMode.CAUTION:
        influence.update({'cadence': 'wait_short_bias', 'admission': 'conservative_resume', 'exposure': 'soft_throttle', 'heartbeat': 'reduced_cycle_bias', 'execution_intake': 'soft_reduction', 'session_recovery': 'manual_review_bias'})
    elif mode == GlobalOperatingMode.MONITOR_ONLY:
        influence.update({'cadence': 'monitor_only_windows', 'admission': 'admit_minimal', 'exposure': 'avoid_new_entries', 'heartbeat': 'monitor_only', 'execution_intake': 'blocked', 'session_recovery': 'monitor_only'})
    elif mode == GlobalOperatingMode.RECOVERY_MODE:
        influence.update({'cadence': 'wait_long_bias', 'admission': 'resume_only_recovered', 'exposure': 'throttle_until_stable', 'heartbeat': 'cooldown_favoring', 'execution_intake': 'blocked', 'session_recovery': 'recovery_priority'})
    elif mode == GlobalOperatingMode.THROTTLED:
        influence.update({'cadence': 'wait_long_bias', 'admission': 'defer_low_priority', 'exposure': 'throttle_global', 'heartbeat': 'conservative', 'execution_intake': 'blocked', 'session_recovery': 'manual_review_bias'})
    elif mode == GlobalOperatingMode.BLOCKED:
        influence.update({'cadence': 'stop', 'admission': 'block_new', 'exposure': 'block_new_entries', 'heartbeat': 'blocked', 'execution_intake': 'blocked', 'session_recovery': 'controlled_only'})
    return influence


@transaction.atomic
def decide_and_optionally_apply_mode(*, snapshot: GlobalRuntimePostureSnapshot, auto_apply: bool = True) -> OperatingModeReviewResult:
    tuning = get_runtime_conservative_tuning_profile()
    current_mode = get_active_global_operating_mode()
    target_mode, decision_type, auto_applicable, reason_codes = _derive_target_mode(snapshot)
    target_mode = _with_hysteresis(current_mode=current_mode, proposed_mode=target_mode, snapshot=snapshot)
    governance_backlog_pressure_state = str(
        ((snapshot.metadata or {}).get('linked_models') or {}).get('governance_backlog_pressure_state') or 'NORMAL'
    ).upper()

    if target_mode == current_mode and decision_type != GlobalOperatingModeDecisionType.REQUIRE_MANUAL_MODE_REVIEW:
        decision_type = GlobalOperatingModeDecisionType.KEEP_CURRENT_MODE

    decision_summary = f'Global operating mode review proposes {target_mode} from {current_mode}.'
    if governance_backlog_pressure_state != 'NORMAL':
        decision_summary = (
            f'Global operating mode review proposes {target_mode} from {current_mode} with '
            f'governance backlog pressure {governance_backlog_pressure_state}.'
        )

    decision = GlobalOperatingModeDecision.objects.create(
        linked_posture_snapshot=snapshot,
        current_mode=current_mode,
        target_mode=target_mode,
        decision_type=decision_type,
        decision_status=GlobalOperatingModeDecisionStatus.PROPOSED,
        auto_applicable=auto_applicable,
        decision_summary=decision_summary,
        reason_codes=reason_codes,
        metadata={
            'downstream_influence': build_downstream_influence(mode=target_mode),
            'governance_backlog_pressure_state': governance_backlog_pressure_state,
            'tuning_profile': tuning.profile_name,
        },
    )

    switch_status = GlobalOperatingModeSwitchStatus.SKIPPED
    switch_summary = 'Mode not applied automatically.'

    if auto_apply and auto_applicable and decision_type != GlobalOperatingModeDecisionType.REQUIRE_MANUAL_MODE_REVIEW:
        state = RuntimeModeState.objects.select_for_update().get(pk=get_runtime_state().pk)
        metadata = dict(state.metadata or {})
        metadata[GLOBAL_MODE_METADATA_KEY] = target_mode
        metadata['global_operating_mode_influence'] = build_downstream_influence(mode=target_mode)
        state.metadata = metadata
        state.save(update_fields=['metadata', 'updated_at'])

        decision.decision_status = GlobalOperatingModeDecisionStatus.APPLIED
        decision.metadata = {**(decision.metadata or {}), 'applied_to_runtime_state_id': state.id}
        decision.save(update_fields=['decision_status', 'metadata', 'updated_at'])
        switch_status = GlobalOperatingModeSwitchStatus.APPLIED
        switch_summary = f'Applied global operating mode {target_mode}.'
    elif auto_apply and not auto_applicable:
        decision.decision_status = GlobalOperatingModeDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        switch_status = GlobalOperatingModeSwitchStatus.BLOCKED
        switch_summary = 'Automatic apply blocked; manual review required.'

    switch_record = GlobalOperatingModeSwitchRecord.objects.create(
        linked_mode_decision=decision,
        previous_mode=current_mode,
        applied_mode=target_mode,
        switch_status=switch_status,
        switch_summary=switch_summary,
        metadata={'auto_apply_requested': auto_apply},
    )

    return OperatingModeReviewResult(decision=decision, switch_record=switch_record)


def apply_operating_mode_decision(*, decision: GlobalOperatingModeDecision) -> GlobalOperatingModeSwitchRecord:
    runtime_state = get_runtime_state()
    current_mode = get_active_global_operating_mode()
    if decision.decision_type == GlobalOperatingModeDecisionType.REQUIRE_MANUAL_MODE_REVIEW:
        decision.decision_status = GlobalOperatingModeDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return GlobalOperatingModeSwitchRecord.objects.create(
            linked_mode_decision=decision,
            previous_mode=current_mode,
            applied_mode=decision.target_mode,
            switch_status=GlobalOperatingModeSwitchStatus.BLOCKED,
            switch_summary='Decision requires manual mode review and cannot be auto-applied.',
            metadata={},
        )

    metadata = dict(runtime_state.metadata or {})
    metadata[GLOBAL_MODE_METADATA_KEY] = decision.target_mode
    metadata['global_operating_mode_influence'] = build_downstream_influence(mode=decision.target_mode)
    runtime_state.metadata = metadata
    runtime_state.save(update_fields=['metadata', 'updated_at'])

    decision.decision_status = GlobalOperatingModeDecisionStatus.APPLIED
    decision.metadata = {**(decision.metadata or {}), 'manual_apply': True}
    decision.save(update_fields=['decision_status', 'metadata', 'updated_at'])

    return GlobalOperatingModeSwitchRecord.objects.create(
        linked_mode_decision=decision,
        previous_mode=current_mode,
        applied_mode=decision.target_mode,
        switch_status=GlobalOperatingModeSwitchStatus.APPLIED,
        switch_summary=f'Manually applied global operating mode {decision.target_mode}.',
        metadata={},
    )

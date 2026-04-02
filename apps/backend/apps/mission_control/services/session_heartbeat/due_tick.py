from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.mission_control.models import (
    AutonomousHeartbeatDecisionType,
    AutonomousRuntimeSession,
    AutonomousRuntimeSessionStatus,
    AutonomousRuntimeTickStatus,
    AutonomousTimingDecisionStatus,
    AutonomousTimingDecisionType,
)
from apps.mission_control.services.session_timing.timing import evaluate_session_timing, map_timing_decision_to_heartbeat
from apps.mission_control.services.session_timing.stop_conditions import evaluate_stop_conditions
from apps.mission_control.services.session_timing.recommendation import emit_timing_recommendation
from apps.runtime_governor.services import get_capabilities_for_current_mode
from apps.safety_guard.services import get_safety_status


@dataclass
class DueTickEvaluation:
    decision_type: str
    due_now: bool
    next_due_at: object | None
    reason_codes: list[str]
    summary: str
    metadata: dict


def evaluate_due_tick(*, session: AutonomousRuntimeSession) -> DueTickEvaluation:
    now = timezone.now()
    latest_tick = session.ticks.order_by('-tick_index', '-id').first()

    if session.session_status == AutonomousRuntimeSessionStatus.PAUSED:
        return DueTickEvaluation(
            decision_type=AutonomousHeartbeatDecisionType.PAUSE_SESSION,
            due_now=False,
            next_due_at=None,
            reason_codes=['session_paused'],
            summary='Session is paused; automatic tick execution is disabled.',
            metadata={},
        )

    if session.session_status in {AutonomousRuntimeSessionStatus.STOPPED, AutonomousRuntimeSessionStatus.COMPLETED}:
        return DueTickEvaluation(
            decision_type=AutonomousHeartbeatDecisionType.STOP_SESSION,
            due_now=False,
            next_due_at=None,
            reason_codes=['session_stopped'],
            summary='Session is stopped/completed; no automatic tick execution.',
            metadata={},
        )

    if session.session_status == AutonomousRuntimeSessionStatus.BLOCKED:
        return DueTickEvaluation(
            decision_type=AutonomousHeartbeatDecisionType.BLOCK_SESSION,
            due_now=False,
            next_due_at=None,
            reason_codes=['session_blocked'],
            summary='Session is blocked by governance posture.',
            metadata={},
        )

    safety = get_safety_status()
    if safety.get('kill_switch_enabled') or safety.get('hard_stop_active'):
        return DueTickEvaluation(
            decision_type=AutonomousHeartbeatDecisionType.BLOCK_SESSION,
            due_now=False,
            next_due_at=None,
            reason_codes=['safety_hard_block'],
            summary='Safety hard stop/kill switch prevents automatic tick dispatch.',
            metadata={'safety': safety},
        )

    capabilities = get_capabilities_for_current_mode()
    if not bool(capabilities.get('allow_signal_generation', False) and capabilities.get('allow_proposals', False)):
        return DueTickEvaluation(
            decision_type=AutonomousHeartbeatDecisionType.PAUSE_SESSION,
            due_now=False,
            next_due_at=None,
            reason_codes=['runtime_capability_block'],
            summary='Runtime capabilities do not allow autonomous signal/proposal cycle.',
            metadata={'capabilities': capabilities},
        )

    if session.ticks.filter(tick_status=AutonomousRuntimeTickStatus.STARTED).exists():
        return DueTickEvaluation(
            decision_type=AutonomousHeartbeatDecisionType.WAIT_FOR_NEXT_WINDOW,
            due_now=False,
            next_due_at=now,
            reason_codes=['tick_already_in_progress'],
            summary='A tick is already in progress for this session.',
            metadata={},
        )

    timing_review = evaluate_session_timing(session=session)
    evaluate_stop_conditions(snapshot=timing_review.snapshot, decision_type=timing_review.decision.decision_type)
    emit_timing_recommendation(snapshot=timing_review.snapshot, decision=timing_review.decision)
    heartbeat_decision_type, due_now, timing_summary = map_timing_decision_to_heartbeat(timing_review.decision)
    timing_review.decision.decision_status = AutonomousTimingDecisionStatus.APPLIED
    timing_review.decision.save(update_fields=['decision_status', 'updated_at'])
    if timing_review.decision.decision_type == AutonomousTimingDecisionType.RUN_NOW:
        return DueTickEvaluation(
            decision_type=heartbeat_decision_type,
            due_now=due_now,
            next_due_at=timing_review.decision.next_due_at,
            reason_codes=list(dict.fromkeys([*(timing_review.snapshot.reason_codes or []), 'timing_policy_run_now'])),
            summary=timing_summary,
            metadata={'timing_snapshot_id': timing_review.snapshot.id, 'timing_decision_id': timing_review.decision.id},
        )

    return DueTickEvaluation(
        decision_type=heartbeat_decision_type,
        due_now=due_now,
        next_due_at=timing_review.decision.next_due_at,
        reason_codes=list(dict.fromkeys([*(timing_review.snapshot.reason_codes or []), 'timing_policy_enforced'])),
        summary=timing_summary,
        metadata={'timing_snapshot_id': timing_review.snapshot.id, 'timing_decision_id': timing_review.decision.id},
    )

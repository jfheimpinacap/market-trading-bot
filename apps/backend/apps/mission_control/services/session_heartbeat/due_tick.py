from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.mission_control.models import (
    AutonomousCooldownState,
    AutonomousCooldownStatus,
    AutonomousHeartbeatDecisionType,
    AutonomousRuntimeSession,
    AutonomousRuntimeSessionStatus,
    AutonomousRuntimeTickStatus,
)
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

    cooldown = AutonomousCooldownState.objects.filter(
        linked_session=session,
        cooldown_status=AutonomousCooldownStatus.ACTIVE,
        expires_at__gt=now,
    ).order_by('expires_at').first()
    if cooldown:
        return DueTickEvaluation(
            decision_type=AutonomousHeartbeatDecisionType.SKIP_FOR_COOLDOWN,
            due_now=False,
            next_due_at=cooldown.expires_at,
            reason_codes=list(cooldown.reason_codes or []) + ['active_cooldown'],
            summary=f'Session cooldown active until {cooldown.expires_at.isoformat()}.',
            metadata={'cooldown_id': cooldown.id, 'cooldown_type': cooldown.cooldown_type},
        )

    return DueTickEvaluation(
        decision_type=AutonomousHeartbeatDecisionType.RUN_DUE_TICK,
        due_now=True,
        next_due_at=now,
        reason_codes=['session_running_due_now'],
        summary='Session is running and due for the next cadence tick.',
        metadata={'latest_tick_status': latest_tick.tick_status if latest_tick else None},
    )

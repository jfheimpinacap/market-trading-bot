from __future__ import annotations

from django.shortcuts import get_object_or_404

from apps.mission_control.models import (
    AutonomousCadenceMode,
    AutonomousRuntimeSession,
    AutonomousRuntimeSessionStatus,
)
from apps.mission_control.services.session_runtime.cadence import decide_next_cadence
from apps.mission_control.services.session_runtime.recommendation import emit_session_recommendation
from apps.mission_control.services.session_runtime.session import (
    pause_autonomous_session,
    resume_autonomous_session,
    start_autonomous_session,
    stop_autonomous_session,
)
from apps.mission_control.services.session_runtime.tick import run_autonomous_tick


def start_session(*, profile_slug: str | None = None, runtime_mode: str | None = None) -> AutonomousRuntimeSession:
    return start_autonomous_session(profile_slug=profile_slug, runtime_mode=runtime_mode)


def pause_session(*, session_id: int) -> AutonomousRuntimeSession:
    session = get_object_or_404(AutonomousRuntimeSession, pk=session_id)
    return pause_autonomous_session(session, reason_codes=['manual_pause'])


def resume_session(*, session_id: int) -> AutonomousRuntimeSession:
    session = get_object_or_404(AutonomousRuntimeSession, pk=session_id)
    return resume_autonomous_session(session)


def stop_session(*, session_id: int, reason_codes: list[str] | None = None) -> AutonomousRuntimeSession:
    session = get_object_or_404(AutonomousRuntimeSession, pk=session_id)
    return stop_autonomous_session(session, reason_codes=reason_codes or ['manual_stop'])


def run_tick(*, session_id: int):
    session = get_object_or_404(AutonomousRuntimeSession, pk=session_id)
    previous_tick = session.ticks.order_by('-tick_index', '-id').first()
    cadence = decide_next_cadence(session=session, previous_tick=previous_tick)

    if cadence.cadence_mode == AutonomousCadenceMode.STOP_SESSION:
        stop_autonomous_session(session, reason_codes=list(cadence.cadence_reason_codes or ['stop_by_cadence']))
        session.session_status = AutonomousRuntimeSessionStatus.BLOCKED
        session.save(update_fields=['session_status', 'updated_at'])
    elif cadence.cadence_mode == AutonomousCadenceMode.PAUSE_SESSION:
        pause_autonomous_session(session, reason_codes=list(cadence.cadence_reason_codes or ['pause_by_cadence']))

    tick = run_autonomous_tick(session=session, cadence_decision=cadence)
    recommendation = emit_session_recommendation(cadence_decision=cadence, tick=tick)
    return tick, cadence, recommendation


def build_session_summary() -> dict:
    sessions = AutonomousRuntimeSession.objects.all()
    active = sessions.filter(session_status=AutonomousRuntimeSessionStatus.RUNNING).count()
    paused = sessions.filter(session_status=AutonomousRuntimeSessionStatus.PAUSED).count()
    stopped = sessions.filter(session_status=AutonomousRuntimeSessionStatus.STOPPED).count()
    latest = sessions.order_by('-started_at').first()

    return {
        'active_sessions': active,
        'paused_sessions': paused,
        'stopped_sessions': stopped,
        'session_count': sessions.count(),
        'ticks_executed': sum(s.executed_tick_count for s in sessions[:50]),
        'ticks_skipped': sum(s.skipped_tick_count for s in sessions[:50]),
        'dispatch_count': sum(s.dispatch_count for s in sessions[:50]),
        'closed_outcome_count': sum(s.closed_outcome_count for s in sessions[:50]),
        'latest_session_id': latest.id if latest else None,
    }

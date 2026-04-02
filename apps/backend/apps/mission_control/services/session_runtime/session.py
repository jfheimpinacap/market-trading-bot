from __future__ import annotations

from django.utils import timezone

from apps.mission_control.models import (
    AutonomousRuntimeSession,
    AutonomousRuntimeSessionStatus,
)
from apps.runtime_governor.services import get_runtime_state


def start_autonomous_session(*, profile_slug: str | None = None, runtime_mode: str | None = None, metadata: dict | None = None) -> AutonomousRuntimeSession:
    state = get_runtime_state()
    return AutonomousRuntimeSession.objects.create(
        session_status=AutonomousRuntimeSessionStatus.RUNNING,
        runtime_mode=runtime_mode or state.current_mode,
        profile_slug=(profile_slug or '').strip(),
        metadata=metadata or {},
    )


def pause_autonomous_session(session: AutonomousRuntimeSession, reason_codes: list[str] | None = None) -> AutonomousRuntimeSession:
    session.session_status = AutonomousRuntimeSessionStatus.PAUSED
    session.pause_reason_codes = list(dict.fromkeys([*(session.pause_reason_codes or []), *((reason_codes or []))]))
    session.save(update_fields=['session_status', 'pause_reason_codes', 'updated_at'])
    return session


def resume_autonomous_session(session: AutonomousRuntimeSession) -> AutonomousRuntimeSession:
    session.session_status = AutonomousRuntimeSessionStatus.RUNNING
    session.save(update_fields=['session_status', 'updated_at'])
    return session


def stop_autonomous_session(session: AutonomousRuntimeSession, reason_codes: list[str] | None = None) -> AutonomousRuntimeSession:
    session.session_status = AutonomousRuntimeSessionStatus.STOPPED
    session.stopped_at = timezone.now()
    session.stop_reason_codes = list(dict.fromkeys([*(session.stop_reason_codes or []), *((reason_codes or []))]))
    session.save(update_fields=['session_status', 'stopped_at', 'stop_reason_codes', 'updated_at'])
    return session

from __future__ import annotations

import threading
import time

from django.db import transaction
from django.utils import timezone

from apps.continuous_demo.models import ContinuousDemoCycleRun, ContinuousDemoSession, LoopRuntimeControl, RuntimeStatus, SessionStatus
from apps.continuous_demo.serializers import ContinuousDemoCycleRunSerializer, ContinuousDemoSessionSerializer, LoopRuntimeControlSerializer
from apps.continuous_demo.services.control import get_runtime_control, normalize_settings
from apps.continuous_demo.services.cycle import run_single_cycle
from apps.semi_auto_demo.models import PendingApproval, PendingApprovalStatus

_LOOP_THREADS: dict[int, threading.Thread] = {}
_LOOP_LOCK = threading.Lock()


def _mark_session_finished(session: ContinuousDemoSession, *, status: str, summary: str) -> None:
    session.session_status = status
    session.summary = summary
    session.finished_at = timezone.now()
    session.save(update_fields=['session_status', 'summary', 'finished_at', 'updated_at'])


def _run_loop(session_id: int) -> None:
    while True:
        with transaction.atomic():
            control = get_runtime_control()
            session = ContinuousDemoSession.objects.select_for_update().get(pk=session_id)
            settings = session.settings_snapshot or {}

            if control.kill_switch or not control.enabled or control.stop_requested:
                control.runtime_status = RuntimeStatus.STOPPED
                control.active_session = None
                control.stop_requested = False
                control.pause_requested = False
                control.cycle_in_progress = False
                control.save(update_fields=['runtime_status', 'active_session', 'stop_requested', 'pause_requested', 'cycle_in_progress', 'updated_at'])
                _mark_session_finished(session, status=SessionStatus.STOPPED, summary='Continuous demo session stopped by runtime control.')
                break

            if control.pause_requested or control.runtime_status == RuntimeStatus.PAUSED:
                control.runtime_status = RuntimeStatus.PAUSED
                session.session_status = SessionStatus.PAUSED
                session.save(update_fields=['session_status', 'updated_at'])
                control.last_heartbeat_at = timezone.now()
                control.save(update_fields=['runtime_status', 'last_heartbeat_at', 'updated_at'])
                time.sleep(1)
                continue

            max_cycles = settings.get('max_cycles_per_session')
            if max_cycles and session.total_cycles >= int(max_cycles):
                control.runtime_status = RuntimeStatus.STOPPED
                control.active_session = None
                control.save(update_fields=['runtime_status', 'active_session', 'updated_at'])
                _mark_session_finished(session, status=SessionStatus.STOPPED, summary='Max cycles per session reached.')
                break

            max_auto_total = settings.get('max_auto_trades_total_per_session')
            if max_auto_total is not None and session.total_auto_executed >= int(max_auto_total):
                control.runtime_status = RuntimeStatus.STOPPED
                control.active_session = None
                control.save(update_fields=['runtime_status', 'active_session', 'updated_at'])
                _mark_session_finished(session, status=SessionStatus.STOPPED, summary='Max auto trades per session reached.')
                break

            control.runtime_status = RuntimeStatus.RUNNING
            session.session_status = SessionStatus.RUNNING
            control.last_heartbeat_at = timezone.now()
            control.save(update_fields=['runtime_status', 'last_heartbeat_at', 'updated_at'])
            session.save(update_fields=['session_status', 'updated_at'])

        cycle = run_single_cycle(session=session, settings=settings)

        if cycle.status == 'FAILED' and settings.get('stop_on_error', False):
            with transaction.atomic():
                control = get_runtime_control()
                session = ContinuousDemoSession.objects.select_for_update().get(pk=session_id)
                control.runtime_status = RuntimeStatus.STOPPED
                control.active_session = None
                control.stop_requested = False
                control.save(update_fields=['runtime_status', 'active_session', 'stop_requested', 'updated_at'])
                _mark_session_finished(session, status=SessionStatus.FAILED, summary='Loop stopped because stop_on_error was enabled.')
            break

        interval_seconds = max(2, int(settings.get('cycle_interval_seconds', 30)))
        for _ in range(interval_seconds):
            with transaction.atomic():
                control = get_runtime_control()
                if control.stop_requested or control.kill_switch:
                    break
            time.sleep(1)


def start_session(*, settings_overrides: dict | None = None) -> ContinuousDemoSession:
    settings = normalize_settings(settings_overrides)

    with transaction.atomic():
        control = get_runtime_control()
        if control.kill_switch:
            raise ValueError('Kill switch is active. Disable it before starting a session.')
        if not settings.get('enabled', True):
            raise ValueError('Continuous demo loop is disabled by settings.')
        if control.runtime_status == RuntimeStatus.RUNNING and control.active_session_id:
            raise ValueError(f'Continuous demo loop already running (session {control.active_session_id}).')

        session = ContinuousDemoSession.objects.create(
            session_status=SessionStatus.RUNNING,
            started_at=timezone.now(),
            settings_snapshot=settings,
            summary='Continuous demo session started.',
        )
        control.runtime_status = RuntimeStatus.RUNNING
        control.enabled = settings.get('enabled', True)
        control.stop_requested = False
        control.pause_requested = False
        control.kill_switch = False
        control.active_session = session
        control.last_error = ''
        control.last_heartbeat_at = timezone.now()
        control.save(update_fields=[
            'runtime_status',
            'enabled',
            'stop_requested',
            'pause_requested',
            'kill_switch',
            'active_session',
            'last_error',
            'last_heartbeat_at',
            'updated_at',
        ])

    with _LOOP_LOCK:
        thread = threading.Thread(target=_run_loop, args=(session.id,), daemon=True, name=f'continuous-demo-{session.id}')
        _LOOP_THREADS[session.id] = thread
        thread.start()

    return session


def pause_session() -> ContinuousDemoSession:
    with transaction.atomic():
        control = get_runtime_control()
        if not control.active_session_id:
            raise ValueError('No active continuous demo session to pause.')
        session = ContinuousDemoSession.objects.select_for_update().get(pk=control.active_session_id)
        control.pause_requested = True
        control.runtime_status = RuntimeStatus.PAUSED
        session.session_status = SessionStatus.PAUSED
        control.save(update_fields=['pause_requested', 'runtime_status', 'updated_at'])
        session.save(update_fields=['session_status', 'updated_at'])
    return session


def resume_session() -> ContinuousDemoSession:
    with transaction.atomic():
        control = get_runtime_control()
        if not control.active_session_id:
            raise ValueError('No active continuous demo session to resume.')
        session = ContinuousDemoSession.objects.select_for_update().get(pk=control.active_session_id)
        if session.session_status != SessionStatus.PAUSED:
            raise ValueError('Session is not paused.')
        control.pause_requested = False
        control.runtime_status = RuntimeStatus.RUNNING
        session.session_status = SessionStatus.RUNNING
        control.save(update_fields=['pause_requested', 'runtime_status', 'updated_at'])
        session.save(update_fields=['session_status', 'updated_at'])
    return session


def stop_session(*, kill_switch: bool = False) -> ContinuousDemoSession | None:
    with transaction.atomic():
        control = get_runtime_control()
        if not control.active_session_id:
            control.runtime_status = RuntimeStatus.STOPPED
            if kill_switch:
                control.kill_switch = True
            control.save(update_fields=['runtime_status', 'kill_switch', 'updated_at'])
            return None
        session = ContinuousDemoSession.objects.select_for_update().get(pk=control.active_session_id)
        control.stop_requested = True
        control.pause_requested = False
        if kill_switch:
            control.kill_switch = True
        control.runtime_status = RuntimeStatus.STOPPED
        control.save(update_fields=['stop_requested', 'pause_requested', 'kill_switch', 'runtime_status', 'updated_at'])
        session.session_status = SessionStatus.STOPPED
        session.summary = 'Stop requested. Waiting for loop shutdown.'
        session.save(update_fields=['session_status', 'summary', 'updated_at'])
        return session


def status_snapshot() -> dict:
    control = LoopRuntimeControl.objects.order_by('id').first()
    if not control:
        return {'runtime': None, 'active_session': None, 'latest_cycle': None, 'pending_approvals': 0}

    active_session = control.active_session
    latest_cycle = ContinuousDemoCycleRun.objects.filter(session=active_session).order_by('-cycle_number').first() if active_session else None
    return {
        'runtime': LoopRuntimeControlSerializer(control).data,
        'active_session': ContinuousDemoSessionSerializer(active_session).data if active_session else None,
        'latest_cycle': ContinuousDemoCycleRunSerializer(latest_cycle).data if latest_cycle else None,
        'pending_approvals': PendingApproval.objects.filter(status=PendingApprovalStatus.PENDING).count(),
    }

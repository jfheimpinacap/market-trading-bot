from __future__ import annotations

import threading
import time

from django.conf import settings
from django.db import connections
from django.db import transaction
from django.utils import timezone

from apps.mission_control.models import AutonomousRunnerState, AutonomousRunnerStatus, AutonomousRuntimeSession, AutonomousRuntimeSessionStatus
from apps.mission_control.services.session_heartbeat.run import run_heartbeat_pass

RUNNER_NAME = 'local_autonomous_heartbeat_runner'
_DEFAULT_INTERVAL_SECONDS = 20

_runner_thread: threading.Thread | None = None
_runner_stop_event = threading.Event()
_runner_lock = threading.Lock()


def _get_or_create_state() -> AutonomousRunnerState:
    state, _ = AutonomousRunnerState.objects.get_or_create(runner_name=RUNNER_NAME, defaults={'runner_status': AutonomousRunnerStatus.STOPPED})
    return state


def _run_loop() -> None:
    while not _runner_stop_event.is_set():
        state = _get_or_create_state()
        if state.runner_status != AutonomousRunnerStatus.RUNNING:
            time.sleep(1)
            continue
        run_heartbeat_pass()
        interval_seconds = int((state.metadata or {}).get('heartbeat_interval_seconds', _DEFAULT_INTERVAL_SECONDS))
        _runner_stop_event.wait(max(interval_seconds, 5))


def start_runner() -> AutonomousRunnerState:
    global _runner_thread
    with _runner_lock:
        with transaction.atomic():
            state = AutonomousRunnerState.objects.select_for_update().filter(runner_name=RUNNER_NAME).first() or _get_or_create_state()
            state.runner_status = AutonomousRunnerStatus.RUNNING
            state.active_session_count = AutonomousRuntimeSession.objects.filter(session_status=AutonomousRuntimeSessionStatus.RUNNING).count()
            state.metadata = {**(state.metadata or {}), 'started_at': timezone.now().isoformat()}
            state.save(update_fields=['runner_status', 'active_session_count', 'metadata', 'updated_at'])

        should_spawn_thread = not (connections['default'].vendor == 'sqlite' and 'test' in settings.SETTINGS_MODULE)
        if should_spawn_thread and (_runner_thread is None or not _runner_thread.is_alive()):
            _runner_stop_event.clear()
            _runner_thread = threading.Thread(target=_run_loop, daemon=True, name='autonomous-heartbeat-runner')
            _runner_thread.start()
    return _get_or_create_state()


def pause_runner() -> AutonomousRunnerState:
    state = _get_or_create_state()
    state.runner_status = AutonomousRunnerStatus.PAUSED
    state.save(update_fields=['runner_status', 'updated_at'])
    return state


def resume_runner() -> AutonomousRunnerState:
    return start_runner()


def stop_runner() -> AutonomousRunnerState:
    state = _get_or_create_state()
    state.runner_status = AutonomousRunnerStatus.STOPPED
    state.save(update_fields=['runner_status', 'updated_at'])
    _runner_stop_event.set()
    return state


def get_runner_state() -> AutonomousRunnerState:
    return _get_or_create_state()

from __future__ import annotations

import threading
import time

from django.db import transaction
from django.utils import timezone

from apps.mission_control.models import MissionControlCycle, MissionControlSession, MissionControlSessionStatus
from apps.mission_control.serializers import MissionControlCycleSerializer, MissionControlSessionSerializer, MissionControlStateSerializer
from apps.mission_control.services.cycle_runner import run_mission_control_cycle
from apps.mission_control.services.profiles import get_profile, list_profiles
from apps.mission_control.services.state import get_or_create_state
from apps.runtime_governor.services import get_runtime_state
from apps.safety_guard.services import get_safety_status

_LOOP_THREADS: dict[int, threading.Thread] = {}
_LOOP_LOCK = threading.Lock()


def _run_loop(session_id: int) -> None:
    while True:
        with transaction.atomic():
            state = get_or_create_state()
            session = MissionControlSession.objects.select_for_update().get(pk=session_id)
            safety = get_safety_status()

            if state.stop_requested or safety['kill_switch_enabled'] or safety['hard_stop_active']:
                state.status = MissionControlSessionStatus.STOPPED
                state.active_session = None
                state.stop_requested = False
                state.pause_requested = False
                state.cycle_in_progress = False
                state.save(update_fields=['status', 'active_session', 'stop_requested', 'pause_requested', 'cycle_in_progress', 'updated_at'])
                session.status = MissionControlSessionStatus.STOPPED
                session.finished_at = timezone.now()
                session.summary = 'Mission control loop stopped by control or safety.'
                session.save(update_fields=['status', 'finished_at', 'summary', 'updated_at'])
                break

            if state.pause_requested:
                state.status = MissionControlSessionStatus.PAUSED
                session.status = MissionControlSessionStatus.PAUSED
                state.last_heartbeat_at = timezone.now()
                state.save(update_fields=['status', 'last_heartbeat_at', 'updated_at'])
                session.save(update_fields=['status', 'updated_at'])
                time.sleep(1)
                continue

            max_cycles = (session.metadata or {}).get('max_cycles_per_session')
            if max_cycles and session.cycle_count >= int(max_cycles):
                state.status = MissionControlSessionStatus.STOPPED
                state.active_session = None
                state.save(update_fields=['status', 'active_session', 'updated_at'])
                session.status = MissionControlSessionStatus.STOPPED
                session.finished_at = timezone.now()
                session.summary = 'Mission control session reached max cycles.'
                session.save(update_fields=['status', 'finished_at', 'summary', 'updated_at'])
                break

            state.status = MissionControlSessionStatus.RUNNING
            state.cycle_in_progress = True
            state.last_heartbeat_at = timezone.now()
            session.status = MissionControlSessionStatus.RUNNING
            state.save(update_fields=['status', 'cycle_in_progress', 'last_heartbeat_at', 'updated_at'])
            session.save(update_fields=['status', 'updated_at'])

        cycle = run_mission_control_cycle(session=session, settings=session.metadata or {})

        with transaction.atomic():
            state = get_or_create_state()
            state.cycle_in_progress = False
            state.save(update_fields=['cycle_in_progress', 'updated_at'])

        interval_seconds = max(5, int((session.metadata or {}).get('cycle_interval_seconds', 45)))
        if cycle.status == 'FAILED':
            interval_seconds = 5
        for _ in range(interval_seconds):
            with transaction.atomic():
                state = get_or_create_state()
                if state.stop_requested:
                    break
            time.sleep(1)


def start_session(*, profile_slug: str | None = None, overrides: dict | None = None) -> MissionControlSession:
    profile = get_profile(profile_slug)
    settings = {**profile, **(overrides or {})}
    with transaction.atomic():
        state = get_or_create_state()
        if state.active_session_id and state.status in {MissionControlSessionStatus.RUNNING, MissionControlSessionStatus.PAUSED}:
            raise ValueError(f'Mission control already active (session {state.active_session_id}).')

        session = MissionControlSession.objects.create(
            status=MissionControlSessionStatus.RUNNING,
            started_at=timezone.now(),
            summary='Mission control session started.',
            metadata=settings,
        )
        state.status = MissionControlSessionStatus.RUNNING
        state.active_session = session
        state.profile_slug = settings['slug']
        state.settings_snapshot = settings
        state.pause_requested = False
        state.stop_requested = False
        state.last_error = ''
        state.last_heartbeat_at = timezone.now()
        state.save(update_fields=['status', 'active_session', 'profile_slug', 'settings_snapshot', 'pause_requested', 'stop_requested', 'last_error', 'last_heartbeat_at', 'updated_at'])

    with _LOOP_LOCK:
        thread = threading.Thread(target=_run_loop, args=(session.id,), daemon=True, name=f'mission-control-{session.id}')
        _LOOP_THREADS[session.id] = thread
        thread.start()
    return session


def pause_session() -> MissionControlSession:
    with transaction.atomic():
        state = get_or_create_state()
        if not state.active_session_id:
            raise ValueError('No active mission control session.')
        session = MissionControlSession.objects.select_for_update().get(pk=state.active_session_id)
        state.pause_requested = True
        state.status = MissionControlSessionStatus.PAUSED
        session.status = MissionControlSessionStatus.PAUSED
        state.save(update_fields=['pause_requested', 'status', 'updated_at'])
        session.save(update_fields=['status', 'updated_at'])
        return session


def resume_session() -> MissionControlSession:
    with transaction.atomic():
        state = get_or_create_state()
        if not state.active_session_id:
            raise ValueError('No active mission control session.')
        session = MissionControlSession.objects.select_for_update().get(pk=state.active_session_id)
        state.pause_requested = False
        state.status = MissionControlSessionStatus.RUNNING
        session.status = MissionControlSessionStatus.RUNNING
        state.save(update_fields=['pause_requested', 'status', 'updated_at'])
        session.save(update_fields=['status', 'updated_at'])
        return session


def stop_session() -> MissionControlSession | None:
    with transaction.atomic():
        state = get_or_create_state()
        if not state.active_session_id:
            state.status = MissionControlSessionStatus.STOPPED
            state.stop_requested = False
            state.save(update_fields=['status', 'stop_requested', 'updated_at'])
            return None
        session = MissionControlSession.objects.select_for_update().get(pk=state.active_session_id)
        state.stop_requested = True
        state.pause_requested = False
        state.status = MissionControlSessionStatus.STOPPED
        session.status = MissionControlSessionStatus.STOPPED
        session.summary = 'Stop requested. Waiting for cycle boundary.'
        state.save(update_fields=['stop_requested', 'pause_requested', 'status', 'updated_at'])
        session.save(update_fields=['status', 'summary', 'updated_at'])
        return session


def run_cycle_now(*, profile_slug: str | None = None) -> MissionControlCycle:
    with transaction.atomic():
        state = get_or_create_state()
        session = state.active_session
        if session is None:
            profile = get_profile(profile_slug)
            session = MissionControlSession.objects.create(
                status=MissionControlSessionStatus.RUNNING,
                started_at=timezone.now(),
                summary='Single mission control cycle session.',
                metadata=profile,
            )
        state.cycle_in_progress = True
        state.save(update_fields=['cycle_in_progress', 'updated_at'])

    cycle = run_mission_control_cycle(session=session, settings=session.metadata or {})

    with transaction.atomic():
        state = get_or_create_state()
        if state.active_session_id is None:
            session.status = MissionControlSessionStatus.STOPPED
            session.finished_at = timezone.now()
            session.save(update_fields=['status', 'finished_at', 'updated_at'])
        state.cycle_in_progress = False
        state.save(update_fields=['cycle_in_progress', 'updated_at'])
    return cycle


def status_snapshot() -> dict:
    state = get_or_create_state()
    latest_cycle = MissionControlCycle.objects.filter(session=state.active_session).order_by('-cycle_number').first() if state.active_session else MissionControlCycle.objects.order_by('-started_at').first()
    promotion_summary = None
    try:
        from apps.promotion_committee.services.state import build_promotion_summary

        summary = build_promotion_summary()
        latest = summary.get('latest_run')
        promotion_summary = {
            'latest_recommendation': latest.recommendation_code if latest else None,
            'latest_review_at': latest.created_at.isoformat() if latest else None,
            'is_recommendation_stale': summary.get('is_recommendation_stale', False),
        }
    except Exception:
        promotion_summary = {'latest_recommendation': None, 'latest_review_at': None, 'is_recommendation_stale': False}

    return {
        'state': MissionControlStateSerializer(state).data,
        'active_session': MissionControlSessionSerializer(state.active_session).data if state.active_session else None,
        'latest_cycle': MissionControlCycleSerializer(latest_cycle).data if latest_cycle else None,
        'profiles': list_profiles(),
        'runtime': {'current_mode': get_runtime_state().current_mode, 'status': get_runtime_state().status},
        'safety': get_safety_status(),
        'promotion': promotion_summary,
    }

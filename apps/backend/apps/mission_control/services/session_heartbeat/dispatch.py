from __future__ import annotations

from django.db import transaction

from apps.mission_control.models import (
    AutonomousHeartbeatDecision,
    AutonomousHeartbeatDecisionStatus,
    AutonomousTickDispatchAttempt,
    AutonomousTickDispatchStatus,
)
from apps.mission_control.services.session_runtime import run_tick


def dispatch_due_tick(*, decision: AutonomousHeartbeatDecision) -> AutonomousTickDispatchAttempt:
    attempt = AutonomousTickDispatchAttempt.objects.create(
        linked_session=decision.linked_session,
        linked_heartbeat_decision=decision,
        dispatch_status=AutonomousTickDispatchStatus.QUEUED,
        automatic=True,
        summary='Tick dispatch queued by autonomous heartbeat runner.',
    )

    if not decision.due_now:
        attempt.dispatch_status = AutonomousTickDispatchStatus.SKIPPED
        attempt.summary = 'Dispatch skipped because decision is not due.'
        attempt.save(update_fields=['dispatch_status', 'summary', 'updated_at'])
        decision.decision_status = AutonomousHeartbeatDecisionStatus.SKIPPED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return attempt

    attempt.dispatch_status = AutonomousTickDispatchStatus.STARTED
    attempt.summary = 'Tick dispatch started by autonomous heartbeat runner.'
    attempt.save(update_fields=['dispatch_status', 'summary', 'updated_at'])

    try:
        with transaction.atomic():
            tick, cadence, _recommendation = run_tick(session_id=decision.linked_session_id)
            attempt.linked_tick = tick
            attempt.metadata = {
                'cadence_decision_id': cadence.id,
                'tick_status': tick.tick_status,
            }
            if tick.tick_status in {'COMPLETED', 'PARTIAL'}:
                attempt.dispatch_status = AutonomousTickDispatchStatus.COMPLETED
                decision.decision_status = AutonomousHeartbeatDecisionStatus.EXECUTED
            elif tick.tick_status in {'SKIPPED'}:
                attempt.dispatch_status = AutonomousTickDispatchStatus.SKIPPED
                decision.decision_status = AutonomousHeartbeatDecisionStatus.SKIPPED
            else:
                attempt.dispatch_status = AutonomousTickDispatchStatus.BLOCKED
                decision.decision_status = AutonomousHeartbeatDecisionStatus.BLOCKED
            attempt.summary = f'Automatic tick dispatch finished with tick status {tick.tick_status}.'
            attempt.save(update_fields=['linked_tick', 'metadata', 'dispatch_status', 'summary', 'updated_at'])
            decision.metadata = {**(decision.metadata or {}), 'dispatch_attempt_id': attempt.id}
            decision.save(update_fields=['decision_status', 'metadata', 'updated_at'])
    except Exception as exc:
        attempt.dispatch_status = AutonomousTickDispatchStatus.FAILED
        attempt.summary = f'Automatic tick dispatch failed: {exc}'
        attempt.metadata = {**(attempt.metadata or {}), 'error': str(exc)}
        attempt.save(update_fields=['dispatch_status', 'summary', 'metadata', 'updated_at'])
        decision.decision_status = AutonomousHeartbeatDecisionStatus.BLOCKED
        decision.metadata = {**(decision.metadata or {}), 'dispatch_error': str(exc)}
        decision.save(update_fields=['decision_status', 'metadata', 'updated_at'])

    return attempt

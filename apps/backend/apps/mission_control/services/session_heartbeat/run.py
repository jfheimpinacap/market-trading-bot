from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.mission_control.models import (
    AutonomousHeartbeatDecision,
    AutonomousHeartbeatDecisionStatus,
    AutonomousHeartbeatDecisionType,
    AutonomousHeartbeatRun,
    AutonomousHeartbeatRunnerStatus,
    AutonomousRunnerState,
    AutonomousRunnerStatus,
    AutonomousRuntimeSession,
    AutonomousRuntimeSessionStatus,
    AutonomousSessionAdmissionDecision,
    AutonomousSessionAdmissionDecisionType,
)
from apps.mission_control.services.session_heartbeat.dispatch import dispatch_due_tick
from apps.mission_control.services.session_heartbeat.due_tick import evaluate_due_tick
from apps.mission_control.services.session_heartbeat.recommendation import emit_heartbeat_recommendation
from apps.mission_control.services.session_profile_control import run_profile_selection_review
from apps.runtime_governor.services.tuning_autotriage_auto_sync import run_tuning_autotriage_attention_auto_sync


def _runner_state() -> AutonomousRunnerState:
    from apps.mission_control.services.session_heartbeat.runner import RUNNER_NAME

    state, _ = AutonomousRunnerState.objects.get_or_create(runner_name=RUNNER_NAME, defaults={'runner_status': AutonomousRunnerStatus.STOPPED})
    return state





def _admission_block_reason(session: AutonomousRuntimeSession) -> str | None:
    latest = AutonomousSessionAdmissionDecision.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
    if not latest:
        return None
    blocked_types = {
        AutonomousSessionAdmissionDecisionType.PARK_SESSION,
        AutonomousSessionAdmissionDecisionType.DEFER_SESSION,
        AutonomousSessionAdmissionDecisionType.PAUSE_SESSION,
        AutonomousSessionAdmissionDecisionType.RETIRE_SESSION,
        AutonomousSessionAdmissionDecisionType.REQUIRE_MANUAL_ADMISSION_REVIEW,
    }
    if latest.decision_type in blocked_types:
        return latest.decision_type
    return None

def run_heartbeat_pass() -> AutonomousHeartbeatRun:
    now = timezone.now()
    state = _runner_state()
    profile_review_run = run_profile_selection_review(apply_switches=True)

    sessions = AutonomousRuntimeSession.objects.filter(
        session_status__in=[
            AutonomousRuntimeSessionStatus.RUNNING,
            AutonomousRuntimeSessionStatus.PAUSED,
            AutonomousRuntimeSessionStatus.STOPPED,
            AutonomousRuntimeSessionStatus.BLOCKED,
        ]
    ).order_by('-started_at', '-id')[:50]

    run = AutonomousHeartbeatRun.objects.create(
        started_at=now,
        runner_status=AutonomousHeartbeatRunnerStatus.RUNNING if state.runner_status == AutonomousRunnerStatus.RUNNING else AutonomousHeartbeatRunnerStatus.IDLE,
        considered_session_count=sessions.count(),
    )

    executed_count = 0
    due_count = 0
    wait_count = 0
    cooldown_count = 0
    blocked_count = 0
    paused_count = 0
    stopped_count = 0

    for session in sessions:
        latest_tick = session.ticks.order_by('-tick_index', '-id').first()
        admission_block = _admission_block_reason(session)
        if admission_block:
            decision = AutonomousHeartbeatDecision.objects.create(
                linked_heartbeat_run=run,
                linked_session=session,
                linked_latest_tick=latest_tick,
                decision_type=AutonomousHeartbeatDecisionType.BLOCK_SESSION,
                decision_status=AutonomousHeartbeatDecisionStatus.BLOCKED,
                due_now=False,
                next_due_at=None,
                reason_codes=['global_admission_block', admission_block.lower()],
                decision_summary=f'blocked by global admission decision={admission_block}',
                metadata={'profile_selection_run_id': profile_review_run.id},
            )
            emit_heartbeat_recommendation(decision=decision)
            blocked_count += 1
            continue
        evaluation = evaluate_due_tick(session=session)
        decision_status = AutonomousHeartbeatDecisionStatus.READY if evaluation.due_now else AutonomousHeartbeatDecisionStatus.SKIPPED

        decision = AutonomousHeartbeatDecision.objects.create(
            linked_heartbeat_run=run,
            linked_session=session,
            linked_latest_tick=latest_tick,
            decision_type=evaluation.decision_type,
            decision_status=decision_status,
            due_now=evaluation.due_now,
            next_due_at=evaluation.next_due_at,
            reason_codes=evaluation.reason_codes,
            decision_summary=evaluation.summary,
        metadata={**(evaluation.metadata or {}), 'profile_selection_run_id': profile_review_run.id},
        )
        emit_heartbeat_recommendation(decision=decision)

        if decision.decision_type == AutonomousHeartbeatDecisionType.RUN_DUE_TICK:
            due_count += 1
            dispatch = dispatch_due_tick(decision=decision)
            if dispatch.dispatch_status == 'COMPLETED':
                executed_count += 1
        elif decision.decision_type == AutonomousHeartbeatDecisionType.SKIP_FOR_COOLDOWN:
            cooldown_count += 1
        elif decision.decision_type == AutonomousHeartbeatDecisionType.WAIT_FOR_NEXT_WINDOW:
            wait_count += 1
        elif decision.decision_type in {AutonomousHeartbeatDecisionType.BLOCK_SESSION}:
            blocked_count += 1
        elif decision.decision_type in {AutonomousHeartbeatDecisionType.PAUSE_SESSION}:
            paused_count += 1
        elif decision.decision_type in {AutonomousHeartbeatDecisionType.STOP_SESSION}:
            stopped_count += 1

    runtime_tuning_attention_sync = run_tuning_autotriage_attention_auto_sync()

    run.completed_at = timezone.now()
    run.runner_status = AutonomousHeartbeatRunnerStatus.COMPLETED
    run.due_tick_count = due_count
    run.executed_tick_count = executed_count
    run.wait_count = wait_count
    run.cooldown_skip_count = cooldown_count
    run.blocked_count = blocked_count
    run.paused_count = paused_count
    run.stopped_count = stopped_count
    run.recommendation_summary = (
        f'due={due_count} executed={executed_count} cooldown={cooldown_count} blocked={blocked_count} '
        f'autotriage_sync={runtime_tuning_attention_sync.get("alert_action")}'
    )
    run.metadata = {
        'runner_state': state.runner_status,
        'profile_selection_run_id': profile_review_run.id,
        'runtime_tuning_attention_sync': runtime_tuning_attention_sync,
    }
    run.save()

    with transaction.atomic():
        state = AutonomousRunnerState.objects.select_for_update().get(pk=state.pk)
        state.last_heartbeat_at = run.completed_at
        state.active_session_count = AutonomousRuntimeSession.objects.filter(session_status=AutonomousRuntimeSessionStatus.RUNNING).count()
        if run.runner_status == AutonomousHeartbeatRunnerStatus.COMPLETED:
            state.last_successful_run_at = run.completed_at
        state.save(update_fields=['last_heartbeat_at', 'last_successful_run_at', 'active_session_count', 'updated_at'])

    return run


def build_heartbeat_summary() -> dict:
    latest_run = AutonomousHeartbeatRun.objects.order_by('-started_at', '-id').first()
    runtime_tuning_attention_sync = (latest_run.metadata or {}).get('runtime_tuning_attention_sync', {}) if latest_run else {}
    return {
        'runner_state': {
            'runner_name': _runner_state().runner_name,
            'runner_status': _runner_state().runner_status,
            'last_heartbeat_at': _runner_state().last_heartbeat_at,
            'last_successful_run_at': _runner_state().last_successful_run_at,
            'last_error_at': _runner_state().last_error_at,
            'active_session_count': _runner_state().active_session_count,
            'metadata': _runner_state().metadata,
        },
        'latest_run': latest_run.id if latest_run else None,
        'totals': {
            'heartbeat_runs': AutonomousHeartbeatRun.objects.count(),
            'decisions': AutonomousHeartbeatDecision.objects.count(),
            'dispatch_attempts': sum(r.executed_tick_count for r in AutonomousHeartbeatRun.objects.all()[:100]),
        },
        'runtime_tuning_attention_sync': {
            'attempted': bool(runtime_tuning_attention_sync.get('attempted', False)),
            'success': bool(runtime_tuning_attention_sync.get('success', False)),
            'alert_action': runtime_tuning_attention_sync.get('alert_action'),
            'human_attention_mode': runtime_tuning_attention_sync.get('human_attention_mode'),
            'next_recommended_scope': runtime_tuning_attention_sync.get('next_recommended_scope'),
            'material_change_detected': bool(runtime_tuning_attention_sync.get('material_change_detected', False)),
            'material_change_fields': runtime_tuning_attention_sync.get('material_change_fields', []),
            'update_suppressed': bool(runtime_tuning_attention_sync.get('update_suppressed', False)),
            'suppression_reason': runtime_tuning_attention_sync.get('suppression_reason'),
            'active_alert_present': bool(runtime_tuning_attention_sync.get('active_alert_present', False)),
            'sync_summary': runtime_tuning_attention_sync.get('sync_summary', ''),
        },
    }

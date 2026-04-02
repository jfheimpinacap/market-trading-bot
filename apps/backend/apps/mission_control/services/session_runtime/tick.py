from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.mission_control.models import (
    AutonomousCadenceDecision,
    AutonomousCadenceMode,
    AutonomousMissionRuntimeRun,
    AutonomousMissionRuntimeStatus,
    AutonomousRuntimeSession,
    AutonomousRuntimeSessionStatus,
    AutonomousRuntimeTick,
    AutonomousRuntimeTickMode,
    AutonomousRuntimeTickStatus,
)
from apps.mission_control.services.autonomous_runtime.cycle_execution import execute_cycle_plan
from apps.mission_control.services.autonomous_runtime.cycle_outcome import build_cycle_outcome
from apps.mission_control.services.autonomous_runtime.cycle_plan import build_cycle_plan
from apps.mission_control.services.autonomous_runtime.recommendation import emit_recommendation
from apps.mission_control.services.profiles import get_profile


def _tick_mode_from_cadence(cadence_mode: str) -> str:
    if cadence_mode == AutonomousCadenceMode.MONITOR_ONLY_NEXT:
        return AutonomousRuntimeTickMode.MONITOR_ONLY
    if cadence_mode in {AutonomousCadenceMode.WAIT_LONG, AutonomousCadenceMode.WAIT_SHORT}:
        return AutonomousRuntimeTickMode.SKIP
    return AutonomousRuntimeTickMode.FULL_CYCLE


def run_autonomous_tick(*, session: AutonomousRuntimeSession, cadence_decision: AutonomousCadenceDecision) -> AutonomousRuntimeTick:
    tick = AutonomousRuntimeTick.objects.create(
        linked_session=session,
        tick_index=session.tick_count + 1,
        planned_tick_mode=_tick_mode_from_cadence(cadence_decision.cadence_mode),
        tick_status=AutonomousRuntimeTickStatus.PLANNED,
        reason_codes=list(cadence_decision.cadence_reason_codes or []),
    )

    if session.session_status in {AutonomousRuntimeSessionStatus.STOPPED, AutonomousRuntimeSessionStatus.BLOCKED, AutonomousRuntimeSessionStatus.COMPLETED}:
        tick.tick_status = AutonomousRuntimeTickStatus.BLOCKED
        tick.tick_summary = 'Tick blocked because session is not runnable.'
        tick.save(update_fields=['tick_status', 'tick_summary', 'updated_at'])
        return tick

    if cadence_decision.cadence_mode in {AutonomousCadenceMode.STOP_SESSION, AutonomousCadenceMode.PAUSE_SESSION, AutonomousCadenceMode.WAIT_LONG, AutonomousCadenceMode.WAIT_SHORT}:
        tick.tick_status = AutonomousRuntimeTickStatus.SKIPPED
        tick.tick_summary = f'Tick skipped by cadence decision {cadence_decision.cadence_mode}.'
        tick.save(update_fields=['tick_status', 'tick_summary', 'updated_at'])
        session.tick_count += 1
        session.skipped_tick_count += 1
        session.save(update_fields=['tick_count', 'skipped_tick_count', 'updated_at'])
        return tick

    tick.tick_status = AutonomousRuntimeTickStatus.STARTED
    tick.save(update_fields=['tick_status', 'updated_at'])

    with transaction.atomic():
        profile = get_profile(session.profile_slug or None)
        runtime_run = AutonomousMissionRuntimeRun.objects.create(
            started_at=timezone.now(),
            runtime_status=AutonomousMissionRuntimeStatus.RUNNING,
            cycle_count=1,
            metadata={
                'session_id': session.id,
                'tick_id': tick.id,
                'planned_tick_mode': tick.planned_tick_mode,
            },
        )
        cycle_plan = build_cycle_plan(runtime_run=runtime_run)

        if tick.planned_tick_mode == AutonomousRuntimeTickMode.MONITOR_ONLY:
            flags = dict(cycle_plan.planned_step_flags or {})
            flags['execution_intake'] = False
            cycle_plan.planned_step_flags = flags
            cycle_plan.plan_status = 'REDUCED'
            cycle_plan.reason_codes = list(dict.fromkeys([*(cycle_plan.reason_codes or []), 'monitor_only_tick']))
            cycle_plan.plan_summary = 'Monitor-only tick forced by cadence decision.'
            cycle_plan.save(update_fields=['planned_step_flags', 'plan_status', 'reason_codes', 'plan_summary', 'updated_at'])

        runtime_rec = emit_recommendation(runtime_run=runtime_run, cycle_plan=cycle_plan)
        cycle_execution = execute_cycle_plan(cycle_plan=cycle_plan, mission_session=None, mission_settings=profile)
        cycle_outcome = build_cycle_outcome(cycle_execution=cycle_execution)

        runtime_run.executed_cycle_count = 1 if cycle_execution.execution_status in {'COMPLETED', 'PARTIAL'} else 0
        runtime_run.blocked_cycle_count = 1 if cycle_execution.execution_status == 'BLOCKED' else 0
        runtime_run.dispatch_count = cycle_outcome.dispatch_count
        runtime_run.closed_outcome_count = cycle_outcome.close_action_count
        runtime_run.postmortem_handoff_count = cycle_outcome.postmortem_count
        runtime_run.learning_handoff_count = cycle_outcome.learning_count
        runtime_run.reuse_applied_count = cycle_outcome.reuse_count
        runtime_run.recommendation_summary = runtime_rec.recommendation_type
        runtime_run.runtime_status = AutonomousMissionRuntimeStatus.COMPLETED if runtime_run.blocked_cycle_count == 0 else AutonomousMissionRuntimeStatus.DEGRADED
        runtime_run.completed_at = timezone.now()
        runtime_run.save()

    tick.linked_runtime_run = runtime_run
    tick.linked_cycle_plan = cycle_plan
    tick.linked_cycle_execution = cycle_execution
    tick.linked_cycle_outcome = cycle_outcome
    tick.metadata = {'runtime_recommendation': runtime_rec.recommendation_type}
    tick.tick_status = AutonomousRuntimeTickStatus.PARTIAL if cycle_execution.execution_status == 'PARTIAL' else AutonomousRuntimeTickStatus.COMPLETED
    tick.tick_summary = f'Tick executed with {cycle_plan.plan_status} plan and {cycle_outcome.outcome_status} outcome.'
    tick.save()

    session.tick_count += 1
    session.executed_tick_count += 1
    session.dispatch_count += cycle_outcome.dispatch_count
    session.closed_outcome_count += cycle_outcome.close_action_count
    session.metadata = {**(session.metadata or {}), 'last_runtime_run_id': runtime_run.id}
    session.save(update_fields=['tick_count', 'executed_tick_count', 'dispatch_count', 'closed_outcome_count', 'metadata', 'updated_at'])
    return tick

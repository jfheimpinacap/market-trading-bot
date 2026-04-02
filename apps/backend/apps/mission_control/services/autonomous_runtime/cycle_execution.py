from __future__ import annotations

from apps.mission_control.models import (
    AutonomousMissionCycleExecution,
    AutonomousMissionCycleExecutionStatus,
    AutonomousMissionCyclePlan,
    MissionControlSession,
    MissionControlSessionStatus,
)
from apps.mission_control.services.cycle_runner import run_mission_control_cycle
from django.utils import timezone


def execute_cycle_plan(
    *,
    cycle_plan: AutonomousMissionCyclePlan,
    mission_session: MissionControlSession | None,
    mission_settings: dict,
) -> AutonomousMissionCycleExecution:
    execution = AutonomousMissionCycleExecution.objects.create(
        linked_cycle_plan=cycle_plan,
        execution_status=AutonomousMissionCycleExecutionStatus.STARTED,
    )

    if cycle_plan.plan_status in {'BLOCKED', 'SKIPPED'}:
        execution.execution_status = AutonomousMissionCycleExecutionStatus.BLOCKED
        execution.blocked_steps = ['execution_intake']
        execution.skipped_steps = [k for k, v in (cycle_plan.planned_step_flags or {}).items() if v]
        execution.execution_summary = 'Cycle execution blocked by plan status.'
        execution.save(update_fields=['execution_status', 'blocked_steps', 'skipped_steps', 'execution_summary', 'updated_at'])
        return execution

    step_flags = cycle_plan.planned_step_flags or {}
    executed_steps = [k for k, v in step_flags.items() if v]
    skipped_steps = [k for k, v in step_flags.items() if not v]

    if mission_session is None:
        mission_session = MissionControlSession.objects.create(
            status=MissionControlSessionStatus.RUNNING,
            started_at=timezone.now(),
            summary='Session created by autonomous runtime tick executor.',
            metadata={'source': 'autonomous_runtime_tick'},
        )

    mission_cycle = run_mission_control_cycle(session=mission_session, settings=mission_settings)
    execution.linked_scan_run = str(mission_cycle.id)
    execution.linked_pursuit_run = str(mission_cycle.id)
    execution.linked_prediction_intake_run = str(mission_cycle.id)
    execution.linked_risk_intake_run = str(mission_cycle.id)
    execution.linked_execution_intake_run = str(mission_cycle.id) if step_flags.get('execution_intake') else ''
    execution.linked_position_watch_run = str(mission_cycle.id)
    execution.linked_outcome_handoff_run = str(mission_cycle.id)
    execution.linked_feedback_reuse_run = str(mission_cycle.id)
    execution.executed_steps = executed_steps
    execution.skipped_steps = skipped_steps
    execution.metadata = {
        'mission_cycle_id': mission_cycle.id,
        'mission_cycle_status': mission_cycle.status,
        'mission_cycle_summary': mission_cycle.summary,
    }
    execution.execution_summary = 'Cycle orchestration executed via mission_control + autonomous trader bridge.'
    execution.execution_status = (
        AutonomousMissionCycleExecutionStatus.PARTIAL if mission_cycle.status == 'PARTIAL' else AutonomousMissionCycleExecutionStatus.COMPLETED
    )
    execution.save()
    return execution

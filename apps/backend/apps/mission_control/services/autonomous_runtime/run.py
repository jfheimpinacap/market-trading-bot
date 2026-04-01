from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.mission_control.models import (
    AutonomousMissionRuntimeRun,
    AutonomousMissionRuntimeStatus,
    MissionControlSession,
    MissionControlSessionStatus,
)
from apps.mission_control.services.autonomous_runtime.cycle_execution import execute_cycle_plan
from apps.mission_control.services.autonomous_runtime.cycle_outcome import build_cycle_outcome
from apps.mission_control.services.autonomous_runtime.cycle_plan import build_cycle_plan
from apps.mission_control.services.autonomous_runtime.recommendation import emit_recommendation
from apps.mission_control.services.profiles import get_profile


def run_autonomous_runtime(*, cycle_count: int = 1, profile_slug: str | None = None) -> AutonomousMissionRuntimeRun:
    settings = get_profile(profile_slug)
    session = MissionControlSession.objects.create(
        status=MissionControlSessionStatus.RUNNING,
        started_at=timezone.now(),
        summary='Autonomous runtime run created mission session.',
        metadata=settings,
    )
    runtime_run = AutonomousMissionRuntimeRun.objects.create(
        started_at=timezone.now(),
        runtime_status=AutonomousMissionRuntimeStatus.RUNNING,
        cycle_count=max(1, int(cycle_count)),
        metadata={'profile_slug': settings['slug'], 'mission_session_id': session.id, 'mission_settings': settings},
    )

    for _ in range(runtime_run.cycle_count):
        with transaction.atomic():
            plan = build_cycle_plan(runtime_run=runtime_run)
            recommendation = emit_recommendation(runtime_run=runtime_run, cycle_plan=plan)
            execution = execute_cycle_plan(cycle_plan=plan, mission_session=session, mission_settings=settings)
            outcome = build_cycle_outcome(cycle_execution=execution)

            runtime_run.executed_cycle_count += 1 if execution.execution_status in {'COMPLETED', 'PARTIAL'} else 0
            runtime_run.blocked_cycle_count += 1 if execution.execution_status == 'BLOCKED' else 0
            runtime_run.dispatch_count += outcome.dispatch_count
            runtime_run.closed_outcome_count += outcome.close_action_count
            runtime_run.postmortem_handoff_count += outcome.postmortem_count
            runtime_run.learning_handoff_count += outcome.learning_count
            runtime_run.reuse_applied_count += outcome.reuse_count
            runtime_run.recommendation_summary = recommendation.recommendation_type
            runtime_run.runtime_status = (
                AutonomousMissionRuntimeStatus.BLOCKED if runtime_run.blocked_cycle_count else AutonomousMissionRuntimeStatus.RUNNING
            )
            runtime_run.save()

    runtime_run.completed_at = timezone.now()
    runtime_run.runtime_status = AutonomousMissionRuntimeStatus.COMPLETED if runtime_run.blocked_cycle_count == 0 else AutonomousMissionRuntimeStatus.DEGRADED
    runtime_run.save(update_fields=[
        'completed_at',
        'runtime_status',
        'executed_cycle_count',
        'blocked_cycle_count',
        'dispatch_count',
        'closed_outcome_count',
        'postmortem_handoff_count',
        'learning_handoff_count',
        'reuse_applied_count',
        'recommendation_summary',
        'updated_at',
    ])
    session.status = MissionControlSessionStatus.STOPPED
    session.finished_at = timezone.now()
    session.summary = 'Autonomous runtime batch completed.'
    session.save(update_fields=['status', 'finished_at', 'summary', 'updated_at'])
    return runtime_run


def build_autonomous_runtime_summary() -> dict:
    latest = AutonomousMissionRuntimeRun.objects.order_by('-started_at').first()
    return {
        'latest_runtime_run_id': latest.id if latest else None,
        'runtime_run_count': AutonomousMissionRuntimeRun.objects.count(),
        'cycle_plan_count': sum(run.cycle_plans.count() for run in AutonomousMissionRuntimeRun.objects.all()[:20]),
        'cycle_execution_count': sum(plan.execution is not None for run in AutonomousMissionRuntimeRun.objects.all()[:20] for plan in run.cycle_plans.all()),
        'cycle_outcome_count': sum(
            1
            for run in AutonomousMissionRuntimeRun.objects.all()[:20]
            for plan in run.cycle_plans.all()
            if hasattr(plan, 'execution') and hasattr(plan.execution, 'outcome')
        ),
        'totals': {
            'dispatch_count': sum(run.dispatch_count for run in AutonomousMissionRuntimeRun.objects.all()[:20]),
            'closed_outcome_count': sum(run.closed_outcome_count for run in AutonomousMissionRuntimeRun.objects.all()[:20]),
            'postmortem_handoff_count': sum(run.postmortem_handoff_count for run in AutonomousMissionRuntimeRun.objects.all()[:20]),
            'learning_handoff_count': sum(run.learning_handoff_count for run in AutonomousMissionRuntimeRun.objects.all()[:20]),
            'reuse_applied_count': sum(run.reuse_applied_count for run in AutonomousMissionRuntimeRun.objects.all()[:20]),
        },
    }

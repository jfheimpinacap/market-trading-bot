from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.chaos_lab.models import ChaosRun
from apps.chaos_lab.services.benchmark import build_benchmark
from apps.chaos_lab.services.injection import apply_injection
from apps.chaos_lab.services.observations import collect_observations
from apps.chaos_lab.services.recovery import cleanup_injected_state
from apps.incident_commander.models import DegradedModeState, IncidentRecord
from apps.operator_alerts.models import OperatorAlert
from apps.operator_queue.models import OperatorQueueItem
from apps.rollout_manager.models import StackRolloutRun


def execute_chaos_run(*, experiment, trigger_mode: str = 'manual') -> ChaosRun:
    started_at = timezone.now()
    run = ChaosRun.objects.create(
        experiment=experiment,
        status='RUNNING',
        started_at=started_at,
        trigger_mode=trigger_mode,
        summary='Chaos experiment running.',
        details={'paper_demo_only': True, 'real_execution': False},
    )

    incident_before_ids = set(IncidentRecord.objects.values_list('id', flat=True))
    alerts_before = OperatorAlert.objects.count()
    queue_before = OperatorQueueItem.objects.count()
    rollback_before = StackRolloutRun.objects.filter(status='ROLLED_BACK').count()

    try:
        with transaction.atomic():
            injection_result = apply_injection(experiment=experiment, run=run)
            run.details = {**(run.details or {}), 'injections': injection_result.injections}
            run.save(update_fields=['details', 'updated_at'])

            observations = collect_observations(
                run=run,
                started_at=started_at,
                incident_before_ids=incident_before_ids,
                alert_before=alerts_before,
                queue_before=queue_before,
                rollout_before_rollback_count=rollback_before,
            )

            finished_at = timezone.now()
            degraded_state = DegradedModeState.objects.order_by('-updated_at', '-id').first()
            degraded_mode_triggered = bool(degraded_state and degraded_state.state != 'normal')
            alerts_delta = OperatorAlert.objects.count() - alerts_before
            queue_delta = OperatorQueueItem.objects.count() - queue_before
            rollback_triggered = StackRolloutRun.objects.filter(status='ROLLED_BACK').count() > rollback_before

            benchmark = build_benchmark(
                run=run,
                incident_ids=observations.incident_ids,
                started_at=started_at,
                finished_at=finished_at,
                alerts_delta=alerts_delta,
                queue_delta=queue_delta,
                rollback_triggered=rollback_triggered,
                degraded_mode_triggered=degraded_mode_triggered,
            )

            run.status = 'SUCCESS' if observations.incident_ids else 'PARTIAL'
            run.summary = 'Chaos run completed with incident detection + mitigation evidence.' if observations.incident_ids else 'Chaos run completed without new incidents (valid/noise-safe case).'
            run.finished_at = finished_at
            run.details = {
                **(run.details or {}),
                'benchmark_id': benchmark.id,
                'observation_ids': observations.observation_ids,
                'incident_ids': observations.incident_ids,
            }
            run.save(update_fields=['status', 'summary', 'finished_at', 'details', 'updated_at'])

    except Exception as exc:
        run.status = 'FAILED'
        run.summary = f'Chaos run failed: {exc}'
        run.finished_at = timezone.now()
        run.details = {**(run.details or {}), 'error': str(exc)}
        run.save(update_fields=['status', 'summary', 'finished_at', 'details', 'updated_at'])
    finally:
        cleanup = cleanup_injected_state(run_id=run.id)
        run.details = {**(run.details or {}), 'cleanup': cleanup}
        run.save(update_fields=['details', 'updated_at'])

    return run

from __future__ import annotations

from decimal import Decimal

from apps.chaos_lab.models import ChaosObservation, ResilienceBenchmark
from apps.incident_commander.models import IncidentAction, IncidentRecoveryRun


def _to_decimal(value: float | int | Decimal) -> Decimal:
    return Decimal(str(value))


def build_benchmark(*, run, incident_ids: list[int], started_at, finished_at, alerts_delta: int, queue_delta: int, rollback_triggered: bool, degraded_mode_triggered: bool) -> ResilienceBenchmark:
    detection_seconds = None
    mitigation_seconds = None
    recovery_seconds = None

    detection_obs = ChaosObservation.objects.filter(run=run, code='incident_created').order_by('observed_at', 'id').first()
    mitigate_obs = ChaosObservation.objects.filter(run=run, code='incident_mitigated').order_by('observed_at', 'id').first()
    recovery = IncidentRecoveryRun.objects.filter(incident_id__in=incident_ids, run_status='SUCCESS').order_by('created_at', 'id').first()

    if detection_obs:
        detection_seconds = _to_decimal(max((detection_obs.observed_at - started_at).total_seconds(), 0))
    if mitigate_obs:
        mitigation_seconds = _to_decimal(max((mitigate_obs.observed_at - started_at).total_seconds(), 0))
    if recovery:
        recovery_seconds = _to_decimal(max((recovery.created_at - started_at).total_seconds(), 0))

    total_recovery = max(IncidentRecoveryRun.objects.filter(incident_id__in=incident_ids).count(), 1)
    recovery_success = IncidentRecoveryRun.objects.filter(incident_id__in=incident_ids, run_status='SUCCESS').count()
    recovery_success_rate = _to_decimal(recovery_success / total_recovery)

    action_count = IncidentAction.objects.filter(incident_id__in=incident_ids, action_status='APPLIED').count()

    score = Decimal('100')
    if detection_seconds and detection_seconds > 120:
        score -= Decimal('10')
    if mitigation_seconds and mitigation_seconds > 180:
        score -= Decimal('10')
    if rollback_triggered:
        score -= Decimal('5')
    if not degraded_mode_triggered and incident_ids:
        score -= Decimal('15')
    if recovery_success_rate < Decimal('0.5') and incident_ids:
        score -= Decimal('10')
    score += Decimal(min(action_count, 5))
    score = max(Decimal('0'), min(Decimal('100'), score))

    return ResilienceBenchmark.objects.create(
        run=run,
        experiment=run.experiment,
        detection_time_seconds=detection_seconds,
        mitigation_time_seconds=mitigation_seconds,
        recovery_time_seconds=recovery_seconds,
        incidents_created=len(incident_ids),
        degraded_mode_triggered=degraded_mode_triggered,
        rollback_triggered=rollback_triggered,
        alerts_sent=max(alerts_delta, 0),
        queue_items_created=max(queue_delta, 0),
        recovery_success_rate=recovery_success_rate,
        resilience_score=score,
        metrics={
            'duration_seconds': max((finished_at - started_at).total_seconds(), 0),
            'incident_ids': incident_ids,
            'paper_demo_only': True,
            'actions_applied_count': action_count,
        },
    )

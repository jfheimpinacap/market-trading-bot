from __future__ import annotations

from apps.autonomy_rollout.models import AutonomyRolloutRun, AutonomyRolloutStatus


def build_rollout_summary() -> dict:
    total_runs = AutonomyRolloutRun.objects.count()
    latest = AutonomyRolloutRun.objects.order_by('-created_at', '-id').first()
    active = AutonomyRolloutRun.objects.filter(rollout_status=AutonomyRolloutStatus.OBSERVING).order_by('-created_at', '-id').first()
    freeze_or_rollback = AutonomyRolloutRun.objects.filter(rollout_status__in=[AutonomyRolloutStatus.FREEZE_RECOMMENDED, AutonomyRolloutStatus.ROLLBACK_RECOMMENDED]).count()
    return {
        'total_runs': total_runs,
        'observing_runs': AutonomyRolloutRun.objects.filter(rollout_status=AutonomyRolloutStatus.OBSERVING).count(),
        'stable_runs': AutonomyRolloutRun.objects.filter(rollout_status__in=[AutonomyRolloutStatus.STABLE, AutonomyRolloutStatus.COMPLETED]).count(),
        'freeze_recommended_runs': AutonomyRolloutRun.objects.filter(rollout_status=AutonomyRolloutStatus.FREEZE_RECOMMENDED).count(),
        'rollback_recommended_runs': AutonomyRolloutRun.objects.filter(rollout_status=AutonomyRolloutStatus.ROLLBACK_RECOMMENDED).count(),
        'aborted_runs': AutonomyRolloutRun.objects.filter(rollout_status=AutonomyRolloutStatus.ABORTED).count(),
        'active_run_id': active.id if active else None,
        'latest_run_id': latest.id if latest else None,
        'latest_status': latest.rollout_status if latest else None,
        'domains_with_warning': freeze_or_rollback,
    }

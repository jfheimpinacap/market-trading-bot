from apps.policy_rollout.models import PolicyRolloutRun, PolicyRolloutStatus


def build_rollout_summary() -> dict:
    runs = PolicyRolloutRun.objects.order_by('-created_at', '-id')
    latest = runs.first()
    active = runs.filter(rollout_status=PolicyRolloutStatus.OBSERVING).first()

    return {
        'total_runs': runs.count(),
        'observing_runs': runs.filter(rollout_status=PolicyRolloutStatus.OBSERVING).count(),
        'stable_runs': runs.filter(rollout_status=PolicyRolloutStatus.STABLE).count(),
        'rollback_recommended_runs': runs.filter(rollout_status=PolicyRolloutStatus.ROLLBACK_RECOMMENDED).count(),
        'aborted_runs': runs.filter(rollout_status=PolicyRolloutStatus.ABORTED).count(),
        'latest_run_id': latest.id if latest else None,
        'latest_status': latest.rollout_status if latest else None,
        'active_run_id': active.id if active else None,
    }

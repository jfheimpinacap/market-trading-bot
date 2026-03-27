from apps.replay_lab.models import ReplayRun, ReplayRunStatus
from apps.replay_lab.serializers import ReplayRunSerializer


def build_summary() -> dict:
    latest_run = ReplayRun.objects.order_by('-created_at', '-id').first()
    recent_runs = ReplayRun.objects.order_by('-created_at', '-id')[:5]
    aware_runs = ReplayRun.objects.filter(details__execution_mode='execution_aware').count()
    naive_runs = ReplayRun.objects.filter(details__execution_mode='naive').count()
    return {
        'latest_run': ReplayRunSerializer(latest_run).data if latest_run else None,
        'recent_runs': ReplayRunSerializer(recent_runs, many=True).data,
        'total_runs': ReplayRun.objects.count(),
        'successful_runs': ReplayRun.objects.filter(status=ReplayRunStatus.SUCCESS).count(),
        'execution_modes': {
            'naive_runs': naive_runs,
            'execution_aware_runs': aware_runs,
        },
    }

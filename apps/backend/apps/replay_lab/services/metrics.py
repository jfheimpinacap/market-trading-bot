from apps.replay_lab.models import ReplayRun, ReplayRunStatus
from apps.replay_lab.serializers import ReplayRunSerializer


def build_summary() -> dict:
    latest_run = ReplayRun.objects.order_by('-created_at', '-id').first()
    recent_runs = ReplayRun.objects.order_by('-created_at', '-id')[:5]
    return {
        'latest_run': ReplayRunSerializer(latest_run).data if latest_run else None,
        'recent_runs': ReplayRunSerializer(recent_runs, many=True).data,
        'total_runs': ReplayRun.objects.count(),
        'successful_runs': ReplayRun.objects.filter(status=ReplayRunStatus.SUCCESS).count(),
    }

from django.db.models import Count

from apps.opportunity_supervisor.models import OpportunityCycleItem, OpportunityCycleRun, OpportunityExecutionPath


def build_summary() -> dict:
    latest_run = OpportunityCycleRun.objects.order_by('-started_at', '-id').first()
    by_path = {
        row['execution_path']: row['total']
        for row in OpportunityCycleItem.objects.values('execution_path').annotate(total=Count('id'))
    }
    return {
        'total_cycles': OpportunityCycleRun.objects.count(),
        'latest_cycle': latest_run.id if latest_run else None,
        'opportunities_built': OpportunityCycleItem.objects.count(),
        'proposal_ready': OpportunityCycleItem.objects.exclude(proposal_id=None).count(),
        'queued': by_path.get(OpportunityExecutionPath.QUEUE, 0),
        'auto_executable': by_path.get(OpportunityExecutionPath.AUTO_EXECUTE_PAPER, 0),
        'blocked': by_path.get(OpportunityExecutionPath.BLOCKED, 0),
        'watch': by_path.get(OpportunityExecutionPath.WATCH, 0),
        'paper_demo_only': True,
        'real_execution_enabled': False,
    }

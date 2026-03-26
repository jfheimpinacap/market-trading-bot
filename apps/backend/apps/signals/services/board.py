from django.db.models import Count

from apps.signals.models import OpportunitySignal, OpportunityStatus, SignalFusionRun


def get_board_summary():
    total = OpportunitySignal.objects.count()
    latest_run = SignalFusionRun.objects.order_by('-created_at', '-id').first()

    by_status = OpportunitySignal.objects.values('opportunity_status').annotate(count=Count('id')).order_by('opportunity_status')
    counters = {row['opportunity_status']: row['count'] for row in by_status}

    return {
        'total_opportunities': total,
        'watch_count': counters.get(OpportunityStatus.WATCH, 0),
        'candidate_count': counters.get(OpportunityStatus.CANDIDATE, 0),
        'proposal_ready_count': counters.get(OpportunityStatus.PROPOSAL_READY, 0),
        'blocked_count': counters.get(OpportunityStatus.BLOCKED, 0),
        'latest_run': latest_run,
        'paper_demo_only': True,
        'real_execution_enabled': False,
    }

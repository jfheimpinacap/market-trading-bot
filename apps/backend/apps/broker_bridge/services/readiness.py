from django.db.models import Count

from apps.broker_bridge.models import BrokerDryRun, BrokerDryRunResponse, BrokerIntentStatus, BrokerOrderIntent


def get_readiness_summary() -> dict:
    status_counts = {row['status']: row['count'] for row in BrokerOrderIntent.objects.values('status').annotate(count=Count('id'))}
    dry_counts = {row['simulated_response']: row['count'] for row in BrokerDryRun.objects.values('simulated_response').annotate(count=Count('id'))}

    return {
        'intents_created': BrokerOrderIntent.objects.count(),
        'validated': status_counts.get(BrokerIntentStatus.VALIDATED, 0) + status_counts.get(BrokerIntentStatus.DRY_RUN_READY, 0) + status_counts.get(BrokerIntentStatus.DRY_RUN_EXECUTED, 0),
        'rejected': status_counts.get(BrokerIntentStatus.REJECTED, 0),
        'dry_run_accepted': dry_counts.get(BrokerDryRunResponse.ACCEPTED, 0),
        'dry_run_manual_review': dry_counts.get(BrokerDryRunResponse.NEEDS_MANUAL_REVIEW, 0),
        'status_counts': status_counts,
        'dry_run_response_counts': dry_counts,
    }

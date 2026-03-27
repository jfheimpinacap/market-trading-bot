from apps.venue_account.models import VenueAccountSnapshot, VenueReconciliationIssue, VenueReconciliationRun


def get_current_account_snapshot():
    return VenueAccountSnapshot.objects.order_by('-created_at', '-id').first()


def build_summary() -> dict:
    current = get_current_account_snapshot()
    latest_run = VenueReconciliationRun.objects.order_by('-created_at', '-id').first()
    recent_issues = VenueReconciliationIssue.objects.select_related('reconciliation_run').order_by('-created_at', '-id')[:10]

    return {
        'sandbox_only': True,
        'account_snapshot': {
            'id': current.id,
            'venue_name': current.venue_name,
            'account_mode': current.account_mode,
            'equity': str(current.equity),
            'cash_available': str(current.cash_available),
            'reserved_cash': str(current.reserved_cash),
            'open_positions_count': current.open_positions_count,
            'open_orders_count': current.open_orders_count,
            'created_at': current.created_at,
        } if current else None,
        'latest_reconciliation': {
            'id': latest_run.id,
            'status': latest_run.status,
            'mismatches_count': latest_run.mismatches_count,
            'created_at': latest_run.created_at,
        } if latest_run else None,
        'recent_issues': [
            {
                'id': issue.id,
                'run_id': issue.reconciliation_run_id,
                'issue_type': issue.issue_type,
                'severity': issue.severity,
                'reason': issue.reason,
                'created_at': issue.created_at,
            }
            for issue in recent_issues
        ],
    }

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.incident_commander.models import IncidentRecord, IncidentSeverity, IncidentStatus, IncidentType
from apps.paper_trading.services.portfolio import get_active_account
from apps.venue_account.models import (
    VenueIssueSeverity,
    VenueIssueType,
    VenueOrderMirrorStatus,
    VenuePositionMirrorStatus,
    VenueReconciliationRun,
    VenueReconciliationStatus,
)
from apps.venue_account.services.issues import record_issue
from apps.venue_account.services.mirror import rebuild_sandbox_mirror
from apps.venue_account.services.state import get_current_account_snapshot


@transaction.atomic
def run_reconciliation(metadata: dict | None = None) -> VenueReconciliationRun:
    metadata = metadata or {}
    mirror = rebuild_sandbox_mirror()
    run = VenueReconciliationRun.objects.create(status=VenueReconciliationStatus.PARITY_OK, details={'mirror': mirror, 'metadata': metadata})

    account = get_active_account()
    external_orders = {order.source_paper_order_id: order for order in account.paper_orders.prefetch_related('venue_order_snapshots').all() for order in order.venue_order_snapshots.all()}
    internal_orders = list(account.paper_orders.all())

    mismatches = 0
    for internal_order in internal_orders:
        ext = external_orders.get(internal_order.id)
        if not ext:
            record_issue(
                run=run,
                issue_type=VenueIssueType.MISSING_EXTERNAL_ORDER,
                severity=VenueIssueSeverity.WARNING,
                reason='Internal paper order has no external sandbox mirror order.',
                source_refs={'paper_order_id': internal_order.id},
            )
            mismatches += 1
            continue

        internal_filled = internal_order.requested_quantity - internal_order.remaining_quantity
        if internal_filled != ext.filled_quantity:
            record_issue(
                run=run,
                issue_type=VenueIssueType.FILL_QUANTITY_MISMATCH,
                severity=VenueIssueSeverity.WARNING,
                reason='Filled quantity differs between internal paper order and external mirror order.',
                source_refs={'paper_order_id': internal_order.id, 'external_order_id': ext.external_order_id},
                metadata={'internal_filled': str(internal_filled), 'external_filled': str(ext.filled_quantity)},
            )
            mismatches += 1

    for external in external_orders.values():
        if external.source_paper_order_id is None:
            record_issue(
                run=run,
                issue_type=VenueIssueType.MISSING_INTERNAL_ORDER,
                severity=VenueIssueSeverity.WARNING,
                reason='External mirror order does not map back to an internal paper order.',
                source_refs={'external_order_id': external.external_order_id},
            )
            mismatches += 1

        if external.status == VenueOrderMirrorStatus.REJECTED and external.last_response_status in {'ACCEPTED', 'HOLD'}:
            record_issue(
                run=run,
                issue_type=VenueIssueType.STATUS_MISMATCH,
                severity=VenueIssueSeverity.WARNING,
                reason='External order status is inconsistent with latest normalized response status.',
                source_refs={'external_order_id': external.external_order_id},
                metadata={'status': external.status, 'last_response_status': external.last_response_status},
            )
            mismatches += 1

    external_positions = {position.source_internal_position_id: position for position in account.positions.prefetch_related('venue_position_snapshots').all() for position in position.venue_position_snapshots.all()}
    internal_positions = list(account.positions.all())

    for internal_position in internal_positions:
        ext_position = external_positions.get(internal_position.id)
        if not ext_position:
            record_issue(
                run=run,
                issue_type=VenueIssueType.UNSUPPORTED_MAPPING,
                severity=VenueIssueSeverity.INFO,
                reason='Internal position exists but has no external snapshot mapping.',
                source_refs={'paper_position_id': internal_position.id},
            )
            mismatches += 1
            continue

        if internal_position.quantity != ext_position.quantity:
            record_issue(
                run=run,
                issue_type=VenueIssueType.POSITION_QUANTITY_MISMATCH,
                severity=VenueIssueSeverity.WARNING,
                reason='Position quantity differs between internal and mirror states.',
                source_refs={'paper_position_id': internal_position.id},
                metadata={'internal_quantity': str(internal_position.quantity), 'external_quantity': str(ext_position.quantity)},
            )
            mismatches += 1

    snapshot = get_current_account_snapshot()
    if snapshot:
        if abs(snapshot.cash_available - account.cash_balance) > Decimal('0.01') or abs(snapshot.equity - account.equity) > Decimal('0.01'):
            record_issue(
                run=run,
                issue_type=VenueIssueType.BALANCE_DRIFT,
                severity=VenueIssueSeverity.HIGH,
                reason='Account cash/equity drift detected between internal paper state and external mirror snapshot.',
                source_refs={'account_snapshot_id': snapshot.id, 'paper_account_id': account.id},
                metadata={
                    'snapshot_cash': str(snapshot.cash_available),
                    'paper_cash': str(account.cash_balance),
                    'snapshot_equity': str(snapshot.equity),
                    'paper_equity': str(account.equity),
                },
            )
            mismatches += 1

        if (timezone.now() - snapshot.created_at).total_seconds() > 1800:
            record_issue(
                run=run,
                issue_type=VenueIssueType.STALE_SNAPSHOT,
                severity=VenueIssueSeverity.INFO,
                reason='Latest account snapshot is stale (>30 minutes old).',
                source_refs={'account_snapshot_id': snapshot.id},
            )
            mismatches += 1

    status = VenueReconciliationStatus.PARITY_OK if mismatches == 0 else VenueReconciliationStatus.PARITY_GAP
    run.status = status
    run.orders_compared = len(internal_orders)
    run.positions_compared = len(internal_positions)
    run.balances_compared = 1
    run.mismatches_count = mismatches
    run.summary = 'External mirror parity OK.' if mismatches == 0 else f'External mirror parity gap with {mismatches} mismatches.'
    run.details = {
        **run.details,
        'issues_by_type': {
            issue_type: run.issues.filter(issue_type=issue_type).count()
            for issue_type, _ in VenueIssueType.choices
        },
    }
    run.save(update_fields=['status', 'orders_compared', 'positions_compared', 'balances_compared', 'mismatches_count', 'summary', 'details', 'updated_at'])

    high_issues = run.issues.filter(severity=VenueIssueSeverity.HIGH).count()
    if high_issues:
        IncidentRecord.objects.create(
            incident_type=IncidentType.EXECUTION_ANOMALY,
            severity=IncidentSeverity.WARNING,
            status=IncidentStatus.OPEN,
            title='Venue account mirror parity drift detected',
            summary='Sandbox venue mirror reconciliation detected high-severity drift.',
            source_app='venue_account',
            related_object_type='venue_reconciliation_run',
            related_object_id=str(run.id),
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
            dedupe_key=f'venue-account-run-{run.id}',
            metadata={'high_issues': high_issues, 'mismatches_count': mismatches},
        )

    return run

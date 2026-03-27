from apps.venue_account.models import VenueIssueSeverity, VenueReconciliationIssue, VenueReconciliationRun


def record_issue(
    *,
    run: VenueReconciliationRun,
    issue_type: str,
    reason: str,
    severity: str = VenueIssueSeverity.WARNING,
    source_refs: dict | None = None,
    metadata: dict | None = None,
) -> VenueReconciliationIssue:
    return VenueReconciliationIssue.objects.create(
        reconciliation_run=run,
        issue_type=issue_type,
        severity=severity,
        reason=reason,
        source_refs=source_refs or {},
        metadata=metadata or {},
    )

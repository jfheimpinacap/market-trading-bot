from __future__ import annotations

from apps.mission_control.models import GovernanceReviewPriority, GovernanceReviewSeverity
from apps.mission_control.services.collect import CollectedGovernanceItem


def assign_severity_and_priority(item: CollectedGovernanceItem) -> tuple[str, str]:
    reason_codes = [code.upper() for code in item.reason_codes]
    blockers = [blocker.upper() for blocker in item.blockers]

    has_incident_or_safety = any(
        token in value
        for value in [*reason_codes, *blockers]
        for token in ('SAFETY', 'INCIDENT', 'HARD_BLOCK', 'RUNTIME_BLOCK')
    )
    has_blocker = bool(blockers)
    is_deferred = any('DEFER' in value for value in [*reason_codes, *blockers])
    is_advisory_only = any('ADVISORY' in value for value in reason_codes)

    severity = GovernanceReviewSeverity.INFO
    if has_incident_or_safety and has_blocker:
        severity = GovernanceReviewSeverity.CRITICAL
    elif has_blocker:
        severity = GovernanceReviewSeverity.HIGH
    elif any('CAUTION' in value or 'THROTTLE' in value for value in [*reason_codes, *blockers]):
        severity = GovernanceReviewSeverity.CAUTION

    priority = GovernanceReviewPriority.P4
    if severity == GovernanceReviewSeverity.CRITICAL:
        priority = GovernanceReviewPriority.P1
    elif severity == GovernanceReviewSeverity.HIGH:
        priority = GovernanceReviewPriority.P2
    elif severity == GovernanceReviewSeverity.CAUTION:
        priority = GovernanceReviewPriority.P3

    if has_incident_or_safety and priority != GovernanceReviewPriority.P1:
        priority = GovernanceReviewPriority.P1
    elif is_deferred and priority == GovernanceReviewPriority.P4:
        priority = GovernanceReviewPriority.P3
    elif is_advisory_only and not has_blocker:
        priority = GovernanceReviewPriority.P4

    return severity, priority

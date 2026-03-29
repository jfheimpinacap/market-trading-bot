from __future__ import annotations

from apps.autonomy_backlog.models import GovernanceBacklogPriority
from apps.autonomy_backlog.services.candidates import BacklogCandidate


_PRIORITY_ORDER = {
    GovernanceBacklogPriority.LOW: 1,
    GovernanceBacklogPriority.MEDIUM: 2,
    GovernanceBacklogPriority.HIGH: 3,
    GovernanceBacklogPriority.CRITICAL: 4,
}


def priority_score(priority: str) -> int:
    return _PRIORITY_ORDER.get(priority, 0)


def prioritize_candidate(candidate: BacklogCandidate) -> tuple[str, list[str]]:
    reason_codes: list[str] = []
    if candidate.target_scope == 'manager':
        reason_codes.append('manager_escalation_target')
    if candidate.target_scope == 'operator_review':
        reason_codes.append('operator_review_target')
    if candidate.resolution_status == 'ADOPTED':
        reason_codes.append('adopted_resolution_ready')
    if candidate.resolution_status == 'ACKNOWLEDGED':
        reason_codes.append('acknowledged_resolution_needs_followthrough')

    if candidate.target_scope in {'manager', 'operator_review'}:
        return GovernanceBacklogPriority.CRITICAL, reason_codes
    if candidate.target_scope in {'roadmap', 'scenario'} and candidate.resolution_status == 'ADOPTED':
        return GovernanceBacklogPriority.HIGH, reason_codes
    if candidate.target_scope == 'program':
        return GovernanceBacklogPriority.MEDIUM, reason_codes
    return GovernanceBacklogPriority.LOW, reason_codes

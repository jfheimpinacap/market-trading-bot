from __future__ import annotations

from django.utils import timezone

from apps.autonomy_advisory.models import AdvisoryTargetScope
from apps.autonomy_advisory_resolution.models import AdvisoryResolution, AdvisoryResolutionStatus
from apps.autonomy_backlog.models import (
    GovernanceBacklogItem,
    GovernanceBacklogPriority,
    GovernanceBacklogStatus,
    GovernanceBacklogType,
)
from apps.autonomy_backlog.services.candidates import BacklogCandidate
from apps.autonomy_backlog.services.dedup import find_duplicate_backlog_item
from apps.autonomy_backlog.services.prioritization import prioritize_candidate

BACKLOG_TYPE_BY_SCOPE = {
    AdvisoryTargetScope.ROADMAP: GovernanceBacklogType.ROADMAP_CHANGE_CANDIDATE,
    AdvisoryTargetScope.SCENARIO: GovernanceBacklogType.SCENARIO_CAUTION_CANDIDATE,
    AdvisoryTargetScope.PROGRAM: GovernanceBacklogType.PROGRAM_GOVERNANCE_CANDIDATE,
    AdvisoryTargetScope.MANAGER: GovernanceBacklogType.MANAGER_REVIEW_ITEM,
    AdvisoryTargetScope.OPERATOR_REVIEW: GovernanceBacklogType.OPERATOR_REVIEW_ITEM,
}


def create_backlog_item(*, artifact_id: int, actor: str = 'operator-ui') -> GovernanceBacklogItem:
    resolution = AdvisoryResolution.objects.select_related('advisory_artifact', 'insight', 'campaign').get(advisory_artifact_id=artifact_id)
    if resolution.resolution_status not in {AdvisoryResolutionStatus.ADOPTED, AdvisoryResolutionStatus.ACKNOWLEDGED}:
        raise ValueError('Advisory resolution must be ADOPTED or ACKNOWLEDGED before creating backlog item.')

    backlog_type = BACKLOG_TYPE_BY_SCOPE.get(resolution.advisory_artifact.target_scope)
    if not backlog_type:
        raise ValueError('Advisory target scope is not supported for governance backlog conversion.')

    duplicate = find_duplicate_backlog_item(artifact_id=artifact_id)
    if duplicate:
        return duplicate

    priority, reason_codes = prioritize_candidate(
        BacklogCandidate(
            advisory_artifact=resolution.advisory_artifact_id,
            advisory_resolution=resolution.id,
            insight=resolution.insight_id,
            campaign=resolution.campaign_id,
            campaign_title=resolution.campaign.title if resolution.campaign else None,
            target_scope=resolution.advisory_artifact.target_scope,
            resolution_status=resolution.resolution_status,
            ready_for_backlog=True,
            existing_backlog_item=None,
            blockers=[],
            metadata={},
        )
    )

    return GovernanceBacklogItem.objects.create(
        advisory_artifact=resolution.advisory_artifact,
        advisory_resolution=resolution,
        insight=resolution.insight,
        campaign=resolution.campaign,
        backlog_type=backlog_type,
        backlog_status=GovernanceBacklogStatus.READY,
        priority_level=priority,
        target_scope=resolution.advisory_artifact.target_scope,
        summary=resolution.advisory_artifact.summary,
        rationale=resolution.rationale,
        reason_codes=sorted(set((resolution.reason_codes or []) + reason_codes)),
        blockers=list(resolution.blockers or []),
        created_by=actor,
        metadata={'manual_action': 'create_backlog_item', 'created_at': timezone.now().isoformat()},
    )


def mark_prioritized(*, item_id: int, actor: str = 'operator-ui') -> GovernanceBacklogItem:
    item = GovernanceBacklogItem.objects.get(pk=item_id)
    item.backlog_status = GovernanceBacklogStatus.PRIORITIZED
    if item.priority_level == GovernanceBacklogPriority.LOW:
        item.priority_level = GovernanceBacklogPriority.MEDIUM
    item.metadata = {**(item.metadata or {}), 'manual_action': 'mark_prioritized', 'prioritized_by': actor}
    item.save(update_fields=['backlog_status', 'priority_level', 'metadata', 'updated_at'])
    return item


def mark_deferred(*, item_id: int, actor: str = 'operator-ui') -> GovernanceBacklogItem:
    item = GovernanceBacklogItem.objects.get(pk=item_id)
    item.backlog_status = GovernanceBacklogStatus.DEFERRED
    item.metadata = {**(item.metadata or {}), 'manual_action': 'mark_deferred', 'deferred_by': actor}
    item.save(update_fields=['backlog_status', 'metadata', 'updated_at'])
    return item

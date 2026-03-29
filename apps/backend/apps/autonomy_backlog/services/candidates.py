from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_advisory.models import AdvisoryTargetScope
from apps.autonomy_advisory_resolution.models import AdvisoryResolution, AdvisoryResolutionStatus
from apps.autonomy_backlog.models import GovernanceBacklogItem


@dataclass
class BacklogCandidate:
    advisory_artifact: int
    advisory_resolution: int
    insight: int
    campaign: int | None
    campaign_title: str | None
    target_scope: str
    resolution_status: str
    ready_for_backlog: bool
    existing_backlog_item: int | None
    blockers: list[str]
    metadata: dict


def _is_ready_status(status: str) -> bool:
    return status in {AdvisoryResolutionStatus.ADOPTED, AdvisoryResolutionStatus.ACKNOWLEDGED}


def _candidate_blockers(resolution: AdvisoryResolution, target_scope: str) -> list[str]:
    blockers = list(resolution.blockers or [])
    if target_scope == AdvisoryTargetScope.MEMORY:
        blockers.append('memory_target_out_of_scope_for_governance_backlog')
    if target_scope not in {
        AdvisoryTargetScope.ROADMAP,
        AdvisoryTargetScope.SCENARIO,
        AdvisoryTargetScope.PROGRAM,
        AdvisoryTargetScope.MANAGER,
        AdvisoryTargetScope.OPERATOR_REVIEW,
        AdvisoryTargetScope.MEMORY,
    }:
        blockers.append('unknown_target_scope')
    if not resolution.rationale:
        blockers.append('missing_resolution_rationale')
    return sorted(set(blockers))


def build_backlog_candidates() -> list[BacklogCandidate]:
    rows: list[BacklogCandidate] = []
    existing_map = {
        item.advisory_artifact_id: item
        for item in GovernanceBacklogItem.objects.select_related('advisory_artifact').all()
    }

    resolutions = AdvisoryResolution.objects.select_related('advisory_artifact', 'insight', 'campaign').filter(
        resolution_status__in=[AdvisoryResolutionStatus.ADOPTED, AdvisoryResolutionStatus.ACKNOWLEDGED, AdvisoryResolutionStatus.BLOCKED]
    ).order_by('-updated_at', '-id')[:500]

    for resolution in resolutions:
        target_scope = resolution.advisory_artifact.target_scope
        blockers = _candidate_blockers(resolution, target_scope)
        ready = _is_ready_status(resolution.resolution_status) and not blockers
        existing = existing_map.get(resolution.advisory_artifact_id)

        rows.append(
            BacklogCandidate(
                advisory_artifact=resolution.advisory_artifact_id,
                advisory_resolution=resolution.id,
                insight=resolution.insight_id,
                campaign=resolution.campaign_id,
                campaign_title=resolution.campaign.title if resolution.campaign else None,
                target_scope=target_scope,
                resolution_status=resolution.resolution_status,
                ready_for_backlog=ready,
                existing_backlog_item=existing.id if existing else None,
                blockers=blockers,
                metadata={
                    'resolution_type': resolution.resolution_type,
                    'artifact_type': resolution.advisory_artifact.artifact_type,
                },
            )
        )

    return rows

from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_backlog.models import GovernanceBacklogItem
from apps.autonomy_intake.models import PlanningProposal
from apps.autonomy_intake.services.recommendation import proposal_type_for_backlog_type, target_scope_for_proposal_type


@dataclass
class IntakeCandidate:
    backlog_item: int
    advisory_artifact: int
    insight: int
    campaign: int | None
    campaign_title: str | None
    backlog_type: str
    target_scope: str
    priority_level: str
    ready_for_intake: bool
    existing_proposal: int | None
    blockers: list[str]
    metadata: dict


def _candidate_blockers(item: GovernanceBacklogItem, proposal_type: str | None) -> list[str]:
    blockers = list(item.blockers or [])
    if item.backlog_status not in {'READY', 'PRIORITIZED'}:
        blockers.append('backlog_item_not_ready_or_prioritized')
    if not item.summary:
        blockers.append('missing_backlog_summary')
    if not item.rationale:
        blockers.append('missing_backlog_rationale')
    if proposal_type is None:
        blockers.append('unknown_backlog_type_for_planning_target')
    return sorted(set(blockers))


def build_intake_candidates() -> list[IntakeCandidate]:
    rows: list[IntakeCandidate] = []
    proposal_map = {
        proposal.backlog_item_id: proposal
        for proposal in PlanningProposal.objects.select_related('backlog_item').all()
    }

    items = GovernanceBacklogItem.objects.select_related('campaign').order_by('-updated_at', '-id')[:500]
    for item in items:
        proposal_type = proposal_type_for_backlog_type(item.backlog_type)
        blockers = _candidate_blockers(item, proposal_type)
        existing = proposal_map.get(item.id)
        rows.append(
            IntakeCandidate(
                backlog_item=item.id,
                advisory_artifact=item.advisory_artifact_id,
                insight=item.insight_id,
                campaign=item.campaign_id,
                campaign_title=item.campaign.title if item.campaign else None,
                backlog_type=item.backlog_type,
                target_scope=target_scope_for_proposal_type(proposal_type) if proposal_type else item.target_scope,
                priority_level=item.priority_level,
                ready_for_intake=not blockers,
                existing_proposal=existing.id if existing else None,
                blockers=blockers,
                metadata={'backlog_status': item.backlog_status, 'proposal_type': proposal_type or ''},
            )
        )
    return rows

from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_decision.services.dedup import find_duplicate_decision
from apps.autonomy_decision.services.status import DECISION_BY_PROPOSAL_TYPE, TARGET_BY_PROPOSAL_TYPE
from apps.autonomy_planning_review.models import PlanningProposalResolution, PlanningProposalResolutionStatus


@dataclass
class DecisionCandidate:
    planning_proposal: int
    planning_resolution: int
    backlog_item: int | None
    advisory_artifact: int | None
    insight: int | None
    campaign: int | None
    campaign_title: str | None
    proposal_type: str
    target_scope: str
    priority_level: str
    ready_for_decision: bool
    existing_decision: int | None
    blockers: list[str]
    metadata: dict


def build_decision_candidates() -> list[DecisionCandidate]:
    rows: list[DecisionCandidate] = []
    resolutions = PlanningProposalResolution.objects.select_related('planning_proposal', 'campaign').filter(
        resolution_status=PlanningProposalResolutionStatus.ACCEPTED,
    ).order_by('-updated_at', '-id')[:500]

    for resolution in resolutions:
        proposal = resolution.planning_proposal
        target_scope = TARGET_BY_PROPOSAL_TYPE.get(proposal.proposal_type, proposal.target_scope)
        decision_type = DECISION_BY_PROPOSAL_TYPE.get(proposal.proposal_type)
        duplicate = find_duplicate_decision(proposal_id=proposal.id, target_scope=target_scope)

        blockers = list(resolution.blockers or [])
        if not decision_type:
            blockers.append('unsupported_proposal_type')

        rows.append(
            DecisionCandidate(
                planning_proposal=proposal.id,
                planning_resolution=resolution.id,
                backlog_item=resolution.backlog_item_id,
                advisory_artifact=resolution.advisory_artifact_id,
                insight=resolution.insight_id,
                campaign=resolution.campaign_id,
                campaign_title=resolution.campaign.title if resolution.campaign else None,
                proposal_type=proposal.proposal_type,
                target_scope=target_scope,
                priority_level=proposal.priority_level,
                ready_for_decision=not blockers and duplicate is None,
                existing_decision=duplicate.id if duplicate else None,
                blockers=blockers,
                metadata={
                    'decision_type': decision_type,
                    'resolution_status': resolution.resolution_status,
                },
            )
        )

    return rows

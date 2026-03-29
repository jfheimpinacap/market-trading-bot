from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_intake.models import PlanningProposal, PlanningProposalStatus
from apps.autonomy_planning_review.models import PlanningProposalResolution
from apps.autonomy_planning_review.services.status import evaluate_planning_resolution


@dataclass
class PlanningReviewCandidate:
    planning_proposal: int
    backlog_item: int | None
    advisory_artifact: int | None
    insight: int | None
    campaign: int | None
    campaign_title: str | None
    proposal_type: str
    proposal_status: str
    target_scope: str
    downstream_status: str
    ready_for_resolution: bool
    blockers: list[str]
    metadata: dict


def build_planning_review_candidates() -> list[PlanningReviewCandidate]:
    resolutions = {
        row.planning_proposal_id: row
        for row in PlanningProposalResolution.objects.select_related('planning_proposal').all()
    }

    rows: list[PlanningReviewCandidate] = []
    proposals = PlanningProposal.objects.select_related('backlog_item', 'advisory_artifact', 'insight', 'campaign').filter(
        proposal_status__in=[
            PlanningProposalStatus.EMITTED,
            PlanningProposalStatus.READY,
            PlanningProposalStatus.ACKNOWLEDGED,
            PlanningProposalStatus.BLOCKED,
        ]
    ).order_by('-created_at', '-id')[:500]

    for proposal in proposals:
        existing = resolutions.get(proposal.id)
        evaluation = evaluate_planning_resolution(proposal, existing)
        rows.append(
            PlanningReviewCandidate(
                planning_proposal=proposal.id,
                backlog_item=proposal.backlog_item_id,
                advisory_artifact=proposal.advisory_artifact_id,
                insight=proposal.insight_id,
                campaign=proposal.campaign_id,
                campaign_title=proposal.campaign.title if proposal.campaign else None,
                proposal_type=proposal.proposal_type,
                proposal_status=proposal.proposal_status,
                target_scope=proposal.target_scope,
                downstream_status=evaluation.downstream_status,
                ready_for_resolution=evaluation.ready_for_resolution,
                blockers=evaluation.blockers,
                metadata={
                    'intake_run_id': proposal.metadata.get('intake_run_id') if proposal.metadata else None,
                    'existing_resolution': existing.id if existing else None,
                },
            )
        )
    return rows

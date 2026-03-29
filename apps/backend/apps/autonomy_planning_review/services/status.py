from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_intake.models import PlanningProposal, PlanningProposalStatus, PlanningProposalType
from apps.autonomy_planning_review.models import (
    PlanningProposalResolution,
    PlanningProposalResolutionStatus,
    PlanningProposalResolutionType,
)

TYPE_BY_PROPOSAL = {
    PlanningProposalType.ROADMAP_PROPOSAL: PlanningProposalResolutionType.ROADMAP_PROPOSAL_ACKNOWLEDGED,
    PlanningProposalType.SCENARIO_PROPOSAL: PlanningProposalResolutionType.SCENARIO_PROPOSAL_ACKNOWLEDGED,
    PlanningProposalType.PROGRAM_REVIEW_PROPOSAL: PlanningProposalResolutionType.PROGRAM_REVIEW_ACKNOWLEDGED,
    PlanningProposalType.MANAGER_REVIEW_PROPOSAL: PlanningProposalResolutionType.MANAGER_REVIEW_ACKNOWLEDGED,
    PlanningProposalType.OPERATOR_REVIEW_PROPOSAL: PlanningProposalResolutionType.OPERATOR_REVIEW_ACKNOWLEDGED,
}


@dataclass
class PlanningResolutionEvaluation:
    downstream_status: str
    ready_for_resolution: bool
    blockers: list[str]
    reason_codes: list[str]
    resolution_status: str
    resolution_type: str
    rationale: str


def evaluate_planning_resolution(
    proposal: PlanningProposal,
    existing: PlanningProposalResolution | None = None,
) -> PlanningResolutionEvaluation:
    if existing is not None:
        return PlanningResolutionEvaluation(
            downstream_status=existing.resolution_status,
            ready_for_resolution=existing.resolution_status not in {
                PlanningProposalResolutionStatus.CLOSED,
                PlanningProposalResolutionStatus.ACCEPTED,
            },
            blockers=list(existing.blockers or []),
            reason_codes=list(existing.reason_codes or []),
            resolution_status=existing.resolution_status,
            resolution_type=existing.resolution_type,
            rationale=existing.rationale,
        )

    if proposal.proposal_status == PlanningProposalStatus.BLOCKED:
        return PlanningResolutionEvaluation(
            downstream_status=PlanningProposalResolutionStatus.BLOCKED,
            ready_for_resolution=False,
            blockers=list(proposal.blockers or ['proposal_blocked']),
            reason_codes=['proposal_blocked'],
            resolution_status=PlanningProposalResolutionStatus.BLOCKED,
            resolution_type=PlanningProposalResolutionType.MANUAL_REVIEW_REQUIRED,
            rationale='Planning proposal is blocked and requires manual review before downstream resolution.',
        )

    if proposal.proposal_status not in {PlanningProposalStatus.EMITTED, PlanningProposalStatus.READY, PlanningProposalStatus.ACKNOWLEDGED}:
        return PlanningResolutionEvaluation(
            downstream_status='UNKNOWN',
            ready_for_resolution=False,
            blockers=['proposal_not_emitted_or_ready'],
            reason_codes=['proposal_not_emitted_or_ready'],
            resolution_status=PlanningProposalResolutionStatus.PENDING,
            resolution_type=PlanningProposalResolutionType.MANUAL_REVIEW_REQUIRED,
            rationale='Only emitted/ready/acknowledged planning proposals are eligible for review tracking.',
        )

    status = (
        PlanningProposalResolutionStatus.ACKNOWLEDGED
        if proposal.proposal_status == PlanningProposalStatus.ACKNOWLEDGED
        else PlanningProposalResolutionStatus.PENDING
    )
    reason_codes = ['proposal_acknowledged_in_intake'] if status == PlanningProposalResolutionStatus.ACKNOWLEDGED else ['awaiting_manual_review']
    rationale = (
        'Planning proposal has been acknowledged in intake and awaits accept/defer/reject governance outcome.'
        if status == PlanningProposalResolutionStatus.ACKNOWLEDGED
        else 'Planning proposal emitted and awaiting manual acknowledgment/acceptance decision.'
    )
    return PlanningResolutionEvaluation(
        downstream_status=status,
        ready_for_resolution=True,
        blockers=[],
        reason_codes=reason_codes,
        resolution_status=status,
        resolution_type=TYPE_BY_PROPOSAL.get(proposal.proposal_type, PlanningProposalResolutionType.MANUAL_REVIEW_REQUIRED),
        rationale=rationale,
    )

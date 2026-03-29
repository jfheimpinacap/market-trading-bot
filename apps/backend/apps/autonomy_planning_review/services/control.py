from __future__ import annotations

from django.utils import timezone

from apps.autonomy_intake.models import PlanningProposal, PlanningProposalStatus
from apps.autonomy_planning_review.models import (
    PlanningProposalResolution,
    PlanningProposalResolutionStatus,
    PlanningProposalResolutionType,
)
from apps.autonomy_planning_review.services.status import TYPE_BY_PROPOSAL


def _upsert_resolution(
    *,
    proposal: PlanningProposal,
    actor: str,
    resolution_status: str,
    rationale: str,
    reason_codes: list[str],
) -> PlanningProposalResolution:
    resolution, _ = PlanningProposalResolution.objects.get_or_create(
        planning_proposal=proposal,
        defaults={
            'backlog_item': proposal.backlog_item,
            'advisory_artifact': proposal.advisory_artifact,
            'insight': proposal.insight,
            'campaign': proposal.campaign,
            'resolution_status': resolution_status,
            'resolution_type': TYPE_BY_PROPOSAL.get(proposal.proposal_type, PlanningProposalResolutionType.MANUAL_REVIEW_REQUIRED),
            'rationale': rationale,
            'reason_codes': reason_codes,
            'blockers': [],
            'resolved_by': actor,
            'resolved_at': timezone.now(),
            'linked_target_artifact': proposal.linked_target_artifact,
            'metadata': {'manual_action': resolution_status.lower()},
        },
    )

    if resolution.resolution_status not in {PlanningProposalResolutionStatus.CLOSED, PlanningProposalResolutionStatus.ACCEPTED}:
        resolution.backlog_item = proposal.backlog_item
        resolution.advisory_artifact = proposal.advisory_artifact
        resolution.insight = proposal.insight
        resolution.campaign = proposal.campaign
        resolution.resolution_status = resolution_status
        resolution.resolution_type = TYPE_BY_PROPOSAL.get(proposal.proposal_type, PlanningProposalResolutionType.MANUAL_REVIEW_REQUIRED)
        resolution.rationale = rationale
        resolution.reason_codes = reason_codes
        resolution.blockers = []
        resolution.resolved_by = actor
        resolution.resolved_at = timezone.now()
        resolution.linked_target_artifact = proposal.linked_target_artifact
        resolution.metadata = {**(resolution.metadata or {}), 'manual_action': resolution_status.lower()}
        resolution.save()
    return resolution


def acknowledge_proposal(*, proposal_id: int, actor: str = 'operator-ui') -> PlanningProposalResolution:
    proposal = PlanningProposal.objects.select_related('backlog_item', 'advisory_artifact', 'insight', 'campaign').get(pk=proposal_id)
    proposal.proposal_status = PlanningProposalStatus.ACKNOWLEDGED
    proposal.save(update_fields=['proposal_status', 'updated_at'])
    return _upsert_resolution(
        proposal=proposal,
        actor=actor,
        resolution_status=PlanningProposalResolutionStatus.ACKNOWLEDGED,
        rationale='Planning proposal was manually acknowledged by operator review.',
        reason_codes=['manual_acknowledged'],
    )


def mark_accepted(*, proposal_id: int, actor: str = 'operator-ui', rationale: str | None = None, reason_codes: list[str] | None = None) -> PlanningProposalResolution:
    proposal = PlanningProposal.objects.select_related('backlog_item', 'advisory_artifact', 'insight', 'campaign').get(pk=proposal_id)
    return _upsert_resolution(
        proposal=proposal,
        actor=actor,
        resolution_status=PlanningProposalResolutionStatus.ACCEPTED,
        rationale=rationale or 'Planning proposal was manually accepted as future planning input.',
        reason_codes=reason_codes or ['manual_accepted'],
    )


def mark_deferred(*, proposal_id: int, actor: str = 'operator-ui', rationale: str | None = None, reason_codes: list[str] | None = None) -> PlanningProposalResolution:
    proposal = PlanningProposal.objects.select_related('backlog_item', 'advisory_artifact', 'insight', 'campaign').get(pk=proposal_id)
    return _upsert_resolution(
        proposal=proposal,
        actor=actor,
        resolution_status=PlanningProposalResolutionStatus.DEFERRED,
        rationale=rationale or 'Planning proposal was manually deferred for a later review window.',
        reason_codes=reason_codes or ['manual_deferred'],
    )


def mark_rejected(*, proposal_id: int, actor: str = 'operator-ui', rationale: str | None = None, reason_codes: list[str] | None = None) -> PlanningProposalResolution:
    proposal = PlanningProposal.objects.select_related('backlog_item', 'advisory_artifact', 'insight', 'campaign').get(pk=proposal_id)
    return _upsert_resolution(
        proposal=proposal,
        actor=actor,
        resolution_status=PlanningProposalResolutionStatus.REJECTED,
        rationale=rationale or 'Planning proposal was manually rejected after governance review.',
        reason_codes=reason_codes or ['manual_rejected'],
    )

from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_intake.models import PlanningProposal
from apps.autonomy_planning_review.models import (
    PlanningProposalResolution,
    PlanningProposalResolutionStatus,
    PlanningReviewRecommendation,
    PlanningReviewRun,
)
from apps.autonomy_planning_review.services.candidates import build_planning_review_candidates
from apps.autonomy_planning_review.services.recommendation import build_planning_recommendations
from apps.autonomy_planning_review.services.status import evaluate_planning_resolution


@transaction.atomic
def run_planning_review(*, actor: str = 'operator-ui') -> dict:
    candidates = build_planning_review_candidates()
    run = PlanningReviewRun.objects.create(metadata={'actor': actor})

    proposal_ids = [row.planning_proposal for row in candidates]
    proposals = PlanningProposal.objects.select_related('backlog_item', 'advisory_artifact', 'insight', 'campaign').filter(id__in=proposal_ids)

    pending_count = sum(1 for row in candidates if row.downstream_status == PlanningProposalResolutionStatus.PENDING)
    resolutions: list[PlanningProposalResolution] = []
    recommendations: list[PlanningReviewRecommendation] = []

    for proposal in proposals:
        existing = PlanningProposalResolution.objects.filter(planning_proposal=proposal).first()
        evaluation = evaluate_planning_resolution(proposal, existing)

        resolution, created = PlanningProposalResolution.objects.get_or_create(
            planning_proposal=proposal,
            defaults={
                'backlog_item': proposal.backlog_item,
                'advisory_artifact': proposal.advisory_artifact,
                'insight': proposal.insight,
                'campaign': proposal.campaign,
                'resolution_status': evaluation.resolution_status,
                'resolution_type': evaluation.resolution_type,
                'rationale': evaluation.rationale,
                'reason_codes': evaluation.reason_codes,
                'blockers': evaluation.blockers,
                'linked_target_artifact': proposal.linked_target_artifact,
                'metadata': {'actor': actor, 'source': 'run_review'},
            },
        )

        if not created and resolution.resolution_status not in {PlanningProposalResolutionStatus.CLOSED, PlanningProposalResolutionStatus.ACCEPTED}:
            resolution.backlog_item = proposal.backlog_item
            resolution.advisory_artifact = proposal.advisory_artifact
            resolution.insight = proposal.insight
            resolution.campaign = proposal.campaign
            resolution.resolution_status = evaluation.resolution_status
            resolution.resolution_type = evaluation.resolution_type
            resolution.rationale = evaluation.rationale
            resolution.reason_codes = evaluation.reason_codes
            resolution.blockers = evaluation.blockers
            resolution.linked_target_artifact = proposal.linked_target_artifact
            resolution.metadata = {**(resolution.metadata or {}), 'actor': actor, 'source': 'run_review'}
            resolution.save()

        resolutions.append(resolution)

        for row in build_planning_recommendations(resolution=resolution, pending_count=pending_count):
            recommendations.append(
                PlanningReviewRecommendation.objects.create(
                    review_run=run,
                    planning_proposal=proposal,
                    backlog_item=proposal.backlog_item,
                    recommendation_type=row['recommendation_type'],
                    rationale=row['rationale'],
                    reason_codes=row['reason_codes'],
                    confidence=row['confidence'],
                    blockers=row['blockers'],
                    metadata=row['metadata'],
                )
            )

    run.candidate_count = len(candidates)
    run.pending_count = sum(1 for row in resolutions if row.resolution_status == PlanningProposalResolutionStatus.PENDING)
    run.acknowledged_count = sum(1 for row in resolutions if row.resolution_status == PlanningProposalResolutionStatus.ACKNOWLEDGED)
    run.accepted_count = sum(1 for row in resolutions if row.resolution_status == PlanningProposalResolutionStatus.ACCEPTED)
    run.deferred_count = sum(1 for row in resolutions if row.resolution_status == PlanningProposalResolutionStatus.DEFERRED)
    run.rejected_count = sum(1 for row in resolutions if row.resolution_status == PlanningProposalResolutionStatus.REJECTED)
    run.blocked_count = sum(1 for row in resolutions if row.resolution_status == PlanningProposalResolutionStatus.BLOCKED)
    run.closed_count = sum(1 for row in resolutions if row.resolution_status == PlanningProposalResolutionStatus.CLOSED)
    run.recommendation_summary = dict(Counter(row.recommendation_type for row in recommendations))
    run.save()

    return {'run': run, 'candidates': candidates, 'resolutions': resolutions, 'recommendations': recommendations}

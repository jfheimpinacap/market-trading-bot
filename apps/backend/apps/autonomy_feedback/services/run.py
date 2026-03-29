from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_feedback.models import FeedbackRecommendation, FeedbackRun, FollowupResolution, ResolutionStatus
from apps.autonomy_feedback.services.candidates import build_feedback_candidates
from apps.autonomy_feedback.services.recommendation import build_resolution_recommendations
from apps.autonomy_feedback.services.status import evaluate_downstream
from apps.autonomy_followup.models import CampaignFollowup, FollowupStatus


@transaction.atomic
def run_feedback_review(*, actor: str = 'operator-ui') -> dict:
    candidates = build_feedback_candidates()
    run = FeedbackRun.objects.create(metadata={'actor': actor})

    pending_candidates = [candidate for candidate in candidates if candidate.downstream_status in {'PENDING', 'IN_PROGRESS', 'UNKNOWN'}]

    resolutions: list[FollowupResolution] = []
    recommendations: list[FeedbackRecommendation] = []

    followups = CampaignFollowup.objects.select_related('campaign', 'linked_memory_document', 'linked_postmortem_request').filter(
        id__in=[candidate.followup_id for candidate in candidates],
        followup_status=FollowupStatus.EMITTED,
    )

    for followup in followups:
        evaluation = evaluate_downstream(followup)
        resolution, created = FollowupResolution.objects.get_or_create(
            followup=followup,
            defaults={
                'campaign': followup.campaign,
                'resolution_status': evaluation.resolution_status,
                'downstream_status': evaluation.downstream_status,
                'resolution_type': evaluation.resolution_type,
                'rationale': evaluation.rationale,
                'reason_codes': evaluation.reason_codes,
                'blockers': evaluation.blockers,
                'linked_memory_document': followup.linked_memory_document,
                'linked_postmortem_request': followup.linked_postmortem_request,
                'linked_feedback_artifact': followup.linked_feedback_artifact,
                'metadata': {'actor': actor, 'source': 'run_review'},
            },
        )

        if not created and resolution.resolution_status not in {ResolutionStatus.CLOSED, ResolutionStatus.COMPLETED}:
            resolution.resolution_status = evaluation.resolution_status
            resolution.downstream_status = evaluation.downstream_status
            resolution.resolution_type = evaluation.resolution_type
            resolution.rationale = evaluation.rationale
            resolution.reason_codes = evaluation.reason_codes
            resolution.blockers = evaluation.blockers
            resolution.linked_memory_document = followup.linked_memory_document
            resolution.linked_postmortem_request = followup.linked_postmortem_request
            resolution.linked_feedback_artifact = followup.linked_feedback_artifact
            resolution.metadata = {**(resolution.metadata or {}), 'actor': actor, 'source': 'run_review'}
            resolution.save()

        resolutions.append(resolution)

        for row in build_resolution_recommendations(resolution=resolution, pending_candidate_count=len(pending_candidates)):
            recommendations.append(
                FeedbackRecommendation.objects.create(
                    feedback_run=run,
                    target_campaign_id=row['target_campaign_id'],
                    followup_id=row['followup_id'],
                    followup_type=row['followup_type'],
                    recommendation_type=row['recommendation_type'],
                    rationale=row['rationale'],
                    reason_codes=row['reason_codes'],
                    confidence=row['confidence'],
                    blockers=row['blockers'],
                    metadata=row['metadata'],
                )
            )

    run.candidate_count = len(candidates)
    run.pending_count = sum(1 for row in resolutions if row.resolution_status == ResolutionStatus.PENDING)
    run.in_progress_count = sum(1 for row in resolutions if row.resolution_status == ResolutionStatus.IN_PROGRESS)
    run.completed_count = sum(1 for row in resolutions if row.resolution_status == ResolutionStatus.COMPLETED)
    run.blocked_count = sum(1 for row in resolutions if row.resolution_status == ResolutionStatus.BLOCKED)
    run.rejected_count = sum(1 for row in resolutions if row.resolution_status == ResolutionStatus.REJECTED)
    run.closed_loop_count = sum(1 for row in resolutions if row.resolution_status == ResolutionStatus.CLOSED)
    run.recommendation_summary = dict(Counter(row.recommendation_type for row in recommendations))
    run.save()

    return {'run': run, 'candidates': candidates, 'resolutions': resolutions, 'recommendations': recommendations}

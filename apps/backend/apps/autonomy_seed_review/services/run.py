from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_seed.models import GovernanceSeed
from apps.autonomy_seed_review.models import SeedResolution, SeedResolutionStatus, SeedReviewRecommendation, SeedReviewRun
from apps.autonomy_seed_review.services.candidates import build_seed_review_candidates
from apps.autonomy_seed_review.services.recommendation import build_seed_review_recommendations


@transaction.atomic
def run_seed_resolution_review(*, actor: str = 'operator-ui') -> dict:
    candidates = build_seed_review_candidates()
    run = SeedReviewRun.objects.create(metadata={'actor': actor})

    pending_count = sum(1 for row in candidates if row.downstream_status == SeedResolutionStatus.PENDING)

    recommendations: list[SeedReviewRecommendation] = []
    for candidate in candidates:
        for row in build_seed_review_recommendations(candidate=candidate.__dict__, pending_count=pending_count):
            recommendations.append(
                SeedReviewRecommendation.objects.create(
                    review_run=run,
                    governance_seed_id=candidate.governance_seed,
                    recommendation_type=row['recommendation_type'],
                    rationale=row['rationale'],
                    reason_codes=row['reason_codes'],
                    confidence=row['confidence'],
                    blockers=row['blockers'],
                    metadata=row['metadata'],
                )
            )

    resolutions = SeedResolution.objects.all()
    run.candidate_count = len(candidates)
    run.pending_count = sum(1 for row in candidates if row.downstream_status == SeedResolutionStatus.PENDING)
    run.acknowledged_count = resolutions.filter(resolution_status=SeedResolutionStatus.ACKNOWLEDGED).count()
    run.accepted_count = resolutions.filter(resolution_status=SeedResolutionStatus.ACCEPTED).count()
    run.deferred_count = resolutions.filter(resolution_status=SeedResolutionStatus.DEFERRED).count()
    run.rejected_count = resolutions.filter(resolution_status=SeedResolutionStatus.REJECTED).count()
    run.blocked_count = sum(1 for row in candidates if row.downstream_status == SeedResolutionStatus.BLOCKED)
    run.closed_count = resolutions.filter(resolution_status=SeedResolutionStatus.CLOSED).count()
    run.recommendation_summary = dict(Counter(row.recommendation_type for row in recommendations))
    run.metadata = {**(run.metadata or {}), 'registered_seed_count': GovernanceSeed.objects.count()}
    run.save()

    return {'run': run, 'candidates': candidates, 'recommendations': recommendations}

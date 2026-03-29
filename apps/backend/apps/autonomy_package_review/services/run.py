from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_package.models import GovernancePackage
from apps.autonomy_package_review.models import (
    PackageResolution,
    PackageResolutionStatus,
    PackageReviewRecommendation,
    PackageReviewRun,
)
from apps.autonomy_package_review.services.candidates import build_package_review_candidates
from apps.autonomy_package_review.services.recommendation import build_package_review_recommendations
from apps.autonomy_package_review.services.status import evaluate_package_resolution


@transaction.atomic
def run_package_resolution_review(*, actor: str = 'operator-ui') -> dict:
    candidates = build_package_review_candidates()
    run = PackageReviewRun.objects.create(metadata={'actor': actor})

    package_ids = [row.governance_package for row in candidates]
    packages = GovernancePackage.objects.prefetch_related('linked_decisions').filter(id__in=package_ids)
    pending_count = sum(1 for row in candidates if row.downstream_status == PackageResolutionStatus.PENDING)

    resolutions: list[PackageResolution] = []
    recommendations: list[PackageReviewRecommendation] = []

    for package in packages:
        existing = PackageResolution.objects.filter(governance_package=package).first()
        evaluation = evaluate_package_resolution(package, existing)

        resolution, created = PackageResolution.objects.get_or_create(
            governance_package=package,
            defaults={
                'resolution_status': evaluation.resolution_status,
                'resolution_type': evaluation.resolution_type,
                'rationale': evaluation.rationale,
                'reason_codes': evaluation.reason_codes,
                'blockers': evaluation.blockers,
                'linked_target_artifact': package.linked_target_artifact,
                'metadata': {'actor': actor, 'source': 'run_review'},
            },
        )

        if not created and resolution.resolution_status not in {PackageResolutionStatus.CLOSED, PackageResolutionStatus.ADOPTED}:
            resolution.resolution_status = evaluation.resolution_status
            resolution.resolution_type = evaluation.resolution_type
            resolution.rationale = evaluation.rationale
            resolution.reason_codes = evaluation.reason_codes
            resolution.blockers = evaluation.blockers
            resolution.linked_target_artifact = package.linked_target_artifact
            resolution.metadata = {**(resolution.metadata or {}), 'actor': actor, 'source': 'run_review'}
            resolution.save()

        resolutions.append(resolution)

        for row in build_package_review_recommendations(resolution=resolution, pending_count=pending_count):
            recommendations.append(
                PackageReviewRecommendation.objects.create(
                    review_run=run,
                    governance_package=package,
                    recommendation_type=row['recommendation_type'],
                    rationale=row['rationale'],
                    reason_codes=row['reason_codes'],
                    confidence=row['confidence'],
                    blockers=row['blockers'],
                    metadata=row['metadata'],
                )
            )

    run.candidate_count = len(candidates)
    run.pending_count = sum(1 for row in resolutions if row.resolution_status == PackageResolutionStatus.PENDING)
    run.acknowledged_count = sum(1 for row in resolutions if row.resolution_status == PackageResolutionStatus.ACKNOWLEDGED)
    run.adopted_count = sum(1 for row in resolutions if row.resolution_status == PackageResolutionStatus.ADOPTED)
    run.deferred_count = sum(1 for row in resolutions if row.resolution_status == PackageResolutionStatus.DEFERRED)
    run.rejected_count = sum(1 for row in resolutions if row.resolution_status == PackageResolutionStatus.REJECTED)
    run.blocked_count = sum(1 for row in resolutions if row.resolution_status == PackageResolutionStatus.BLOCKED)
    run.closed_count = sum(1 for row in resolutions if row.resolution_status == PackageResolutionStatus.CLOSED)
    run.recommendation_summary = dict(Counter(row.recommendation_type for row in recommendations))
    run.save()

    return {'run': run, 'candidates': candidates, 'resolutions': resolutions, 'recommendations': recommendations}

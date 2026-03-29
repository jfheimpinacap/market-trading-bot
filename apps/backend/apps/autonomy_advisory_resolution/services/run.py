from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_advisory.models import AdvisoryArtifact
from apps.autonomy_advisory_resolution.models import (
    AdvisoryResolution,
    AdvisoryResolutionRecommendation,
    AdvisoryResolutionRun,
    AdvisoryResolutionStatus,
)
from apps.autonomy_advisory_resolution.services.candidates import build_advisory_resolution_candidates
from apps.autonomy_advisory_resolution.services.recommendation import build_resolution_recommendations
from apps.autonomy_advisory_resolution.services.status import evaluate_artifact_resolution


@transaction.atomic
def run_advisory_resolution_review(*, actor: str = 'operator-ui') -> dict:
    candidates = build_advisory_resolution_candidates()
    run = AdvisoryResolutionRun.objects.create(metadata={'actor': actor})

    artifact_ids = [row.advisory_artifact for row in candidates]
    artifacts = AdvisoryArtifact.objects.select_related('insight', 'campaign').filter(id__in=artifact_ids)

    pending_count = sum(1 for row in candidates if row.downstream_status == AdvisoryResolutionStatus.PENDING)
    resolutions: list[AdvisoryResolution] = []
    recommendations: list[AdvisoryResolutionRecommendation] = []

    for artifact in artifacts:
        existing = AdvisoryResolution.objects.filter(advisory_artifact=artifact).first()
        evaluation = evaluate_artifact_resolution(artifact, existing)

        resolution, created = AdvisoryResolution.objects.get_or_create(
            advisory_artifact=artifact,
            defaults={
                'insight': artifact.insight,
                'campaign': artifact.campaign,
                'resolution_status': evaluation.resolution_status,
                'resolution_type': evaluation.resolution_type,
                'rationale': evaluation.rationale,
                'reason_codes': evaluation.reason_codes,
                'blockers': evaluation.blockers,
                'metadata': {'actor': actor, 'source': 'run_review'},
            },
        )

        if not created and resolution.resolution_status not in {AdvisoryResolutionStatus.CLOSED, AdvisoryResolutionStatus.ADOPTED}:
            resolution.insight = artifact.insight
            resolution.campaign = artifact.campaign
            resolution.resolution_status = evaluation.resolution_status
            resolution.resolution_type = evaluation.resolution_type
            resolution.rationale = evaluation.rationale
            resolution.reason_codes = evaluation.reason_codes
            resolution.blockers = evaluation.blockers
            resolution.metadata = {**(resolution.metadata or {}), 'actor': actor, 'source': 'run_review'}
            resolution.save()

        resolutions.append(resolution)

        for row in build_resolution_recommendations(resolution=resolution, pending_count=pending_count):
            recommendations.append(
                AdvisoryResolutionRecommendation.objects.create(
                    resolution_run=run,
                    advisory_artifact=artifact,
                    insight=artifact.insight,
                    recommendation_type=row['recommendation_type'],
                    rationale=row['rationale'],
                    reason_codes=row['reason_codes'],
                    confidence=row['confidence'],
                    blockers=row['blockers'],
                    metadata=row['metadata'],
                )
            )

    run.candidate_count = len(candidates)
    run.pending_count = sum(1 for row in resolutions if row.resolution_status == AdvisoryResolutionStatus.PENDING)
    run.acknowledged_count = sum(1 for row in resolutions if row.resolution_status == AdvisoryResolutionStatus.ACKNOWLEDGED)
    run.adopted_count = sum(1 for row in resolutions if row.resolution_status == AdvisoryResolutionStatus.ADOPTED)
    run.deferred_count = sum(1 for row in resolutions if row.resolution_status == AdvisoryResolutionStatus.DEFERRED)
    run.rejected_count = sum(1 for row in resolutions if row.resolution_status == AdvisoryResolutionStatus.REJECTED)
    run.blocked_count = sum(1 for row in resolutions if row.resolution_status == AdvisoryResolutionStatus.BLOCKED)
    run.closed_count = sum(1 for row in resolutions if row.resolution_status == AdvisoryResolutionStatus.CLOSED)
    run.recommendation_summary = dict(Counter(row.recommendation_type for row in recommendations))
    run.save()

    return {'run': run, 'candidates': candidates, 'resolutions': resolutions, 'recommendations': recommendations}

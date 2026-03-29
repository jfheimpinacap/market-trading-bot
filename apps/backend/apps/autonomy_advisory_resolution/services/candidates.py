from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_advisory.models import AdvisoryArtifact, AdvisoryArtifactStatus
from apps.autonomy_advisory_resolution.models import AdvisoryResolution
from apps.autonomy_advisory_resolution.services.status import evaluate_artifact_resolution


@dataclass
class AdvisoryResolutionCandidate:
    advisory_artifact: int
    insight: int
    campaign: int | None
    campaign_title: str | None
    artifact_type: str
    artifact_status: str
    target_scope: str
    downstream_status: str
    ready_for_resolution: bool
    blockers: list[str]
    metadata: dict


def build_advisory_resolution_candidates() -> list[AdvisoryResolutionCandidate]:
    resolutions = {
        row.advisory_artifact_id: row
        for row in AdvisoryResolution.objects.select_related('advisory_artifact').all()
    }

    rows: list[AdvisoryResolutionCandidate] = []
    artifacts = AdvisoryArtifact.objects.select_related('insight', 'campaign').filter(
        artifact_status__in=[AdvisoryArtifactStatus.EMITTED, AdvisoryArtifactStatus.BLOCKED]
    ).order_by('-created_at', '-id')[:500]

    for artifact in artifacts:
        evaluation = evaluate_artifact_resolution(artifact, resolutions.get(artifact.id))
        rows.append(
            AdvisoryResolutionCandidate(
                advisory_artifact=artifact.id,
                insight=artifact.insight_id,
                campaign=artifact.campaign_id,
                campaign_title=artifact.campaign.title if artifact.campaign else None,
                artifact_type=artifact.artifact_type,
                artifact_status=artifact.artifact_status,
                target_scope=artifact.target_scope,
                downstream_status=evaluation.downstream_status,
                ready_for_resolution=evaluation.ready_for_resolution,
                blockers=evaluation.blockers,
                metadata={
                    'advisory_run_id': artifact.advisory_run_id,
                    'existing_resolution': resolutions.get(artifact.id).id if resolutions.get(artifact.id) else None,
                },
            )
        )
    return rows

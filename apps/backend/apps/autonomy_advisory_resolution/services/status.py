from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_advisory.models import AdvisoryArtifact, AdvisoryArtifactStatus
from apps.autonomy_advisory_resolution.models import AdvisoryResolution, AdvisoryResolutionStatus, AdvisoryResolutionType


TYPE_BY_SCOPE = {
    'memory': AdvisoryResolutionType.MEMORY_NOTE_ACKNOWLEDGED,
    'roadmap': AdvisoryResolutionType.ROADMAP_NOTE_ACKNOWLEDGED,
    'scenario': AdvisoryResolutionType.SCENARIO_NOTE_ACKNOWLEDGED,
    'program': AdvisoryResolutionType.PROGRAM_NOTE_ACKNOWLEDGED,
    'manager': AdvisoryResolutionType.MANAGER_NOTE_ACKNOWLEDGED,
}


@dataclass
class ResolutionEvaluation:
    downstream_status: str
    ready_for_resolution: bool
    blockers: list[str]
    reason_codes: list[str]
    resolution_status: str
    resolution_type: str
    rationale: str


def evaluate_artifact_resolution(artifact: AdvisoryArtifact, existing: AdvisoryResolution | None = None) -> ResolutionEvaluation:
    if existing is not None:
        return ResolutionEvaluation(
            downstream_status=existing.resolution_status,
            ready_for_resolution=existing.resolution_status not in {AdvisoryResolutionStatus.CLOSED, AdvisoryResolutionStatus.ADOPTED},
            blockers=list(existing.blockers or []),
            reason_codes=list(existing.reason_codes or []),
            resolution_status=existing.resolution_status,
            resolution_type=existing.resolution_type,
            rationale=existing.rationale,
        )

    if artifact.artifact_status == AdvisoryArtifactStatus.BLOCKED:
        return ResolutionEvaluation(
            downstream_status=AdvisoryResolutionStatus.BLOCKED,
            ready_for_resolution=False,
            blockers=list(artifact.blockers or ['artifact_blocked']),
            reason_codes=['artifact_blocked'],
            resolution_status=AdvisoryResolutionStatus.BLOCKED,
            resolution_type=AdvisoryResolutionType.MANUAL_REVIEW_REQUIRED,
            rationale='Advisory artifact is blocked and requires manual review before resolution tracking.',
        )

    if artifact.artifact_status != AdvisoryArtifactStatus.EMITTED:
        return ResolutionEvaluation(
            downstream_status='UNKNOWN',
            ready_for_resolution=False,
            blockers=['artifact_not_emitted'],
            reason_codes=['artifact_not_emitted'],
            resolution_status=AdvisoryResolutionStatus.PENDING,
            resolution_type=AdvisoryResolutionType.MANUAL_REVIEW_REQUIRED,
            rationale='Only emitted advisory artifacts are resolution candidates.',
        )

    resolution_type = TYPE_BY_SCOPE.get(artifact.target_scope, AdvisoryResolutionType.MANUAL_REVIEW_REQUIRED)
    return ResolutionEvaluation(
        downstream_status=AdvisoryResolutionStatus.PENDING,
        ready_for_resolution=True,
        blockers=[],
        reason_codes=['awaiting_manual_review'],
        resolution_status=AdvisoryResolutionStatus.PENDING,
        resolution_type=resolution_type,
        rationale='Advisory artifact emitted and waiting for manual acknowledgment/adoption decision.',
    )

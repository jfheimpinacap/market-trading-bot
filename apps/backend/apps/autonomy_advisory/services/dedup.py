from apps.autonomy_advisory.models import AdvisoryArtifact, AdvisoryArtifactStatus


def find_duplicate_emitted_artifact(*, insight_id: int, artifact_type: str) -> AdvisoryArtifact | None:
    return (
        AdvisoryArtifact.objects.filter(
            insight_id=insight_id,
            artifact_type=artifact_type,
            artifact_status__in=[AdvisoryArtifactStatus.EMITTED, AdvisoryArtifactStatus.ACKNOWLEDGED],
        )
        .order_by('-created_at', '-id')
        .first()
    )

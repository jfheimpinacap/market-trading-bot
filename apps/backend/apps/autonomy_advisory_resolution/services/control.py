from __future__ import annotations

from django.utils import timezone

from apps.autonomy_advisory.models import AdvisoryArtifact, AdvisoryArtifactStatus
from apps.autonomy_advisory_resolution.models import AdvisoryResolution, AdvisoryResolutionStatus, AdvisoryResolutionType
from apps.autonomy_advisory_resolution.services.status import TYPE_BY_SCOPE


def _upsert_resolution(
    *,
    artifact: AdvisoryArtifact,
    actor: str,
    resolution_status: str,
    rationale: str,
    reason_codes: list[str],
) -> AdvisoryResolution:
    resolution_type = TYPE_BY_SCOPE.get(artifact.target_scope, AdvisoryResolutionType.MANUAL_REVIEW_REQUIRED)
    resolution, _ = AdvisoryResolution.objects.get_or_create(
        advisory_artifact=artifact,
        defaults={
            'insight': artifact.insight,
            'campaign': artifact.campaign,
            'resolution_status': resolution_status,
            'resolution_type': resolution_type,
            'rationale': rationale,
            'reason_codes': reason_codes,
            'blockers': [],
            'resolved_by': actor,
            'resolved_at': timezone.now(),
            'linked_artifact': _linked_artifact(artifact),
            'metadata': {'manual_action': resolution_status.lower()},
        },
    )

    if resolution.resolution_status not in {AdvisoryResolutionStatus.CLOSED, AdvisoryResolutionStatus.ADOPTED}:
        resolution.insight = artifact.insight
        resolution.campaign = artifact.campaign
        resolution.resolution_status = resolution_status
        resolution.resolution_type = resolution_type
        resolution.rationale = rationale
        resolution.reason_codes = reason_codes
        resolution.blockers = []
        resolution.resolved_by = actor
        resolution.resolved_at = timezone.now()
        resolution.linked_artifact = _linked_artifact(artifact)
        resolution.metadata = {**(resolution.metadata or {}), 'manual_action': resolution_status.lower()}
        resolution.save()
    return resolution


def _linked_artifact(artifact: AdvisoryArtifact) -> str:
    if artifact.linked_memory_document_id:
        return f'memory:{artifact.linked_memory_document_id}'
    if artifact.linked_program_note:
        return artifact.linked_program_note
    if artifact.linked_feedback_artifact:
        return artifact.linked_feedback_artifact
    return ''


def acknowledge_artifact(*, artifact_id: int, actor: str = 'operator-ui') -> AdvisoryResolution:
    artifact = AdvisoryArtifact.objects.select_related('insight', 'campaign').get(pk=artifact_id)
    artifact.artifact_status = AdvisoryArtifactStatus.ACKNOWLEDGED
    artifact.save(update_fields=['artifact_status', 'updated_at'])
    return _upsert_resolution(
        artifact=artifact,
        actor=actor,
        resolution_status=AdvisoryResolutionStatus.ACKNOWLEDGED,
        rationale='Advisory was manually acknowledged by operator review.',
        reason_codes=['manual_acknowledged'],
    )


def mark_adopted(*, artifact_id: int, actor: str = 'operator-ui', rationale: str | None = None, reason_codes: list[str] | None = None) -> AdvisoryResolution:
    artifact = AdvisoryArtifact.objects.select_related('insight', 'campaign').get(pk=artifact_id)
    return _upsert_resolution(
        artifact=artifact,
        actor=actor,
        resolution_status=AdvisoryResolutionStatus.ADOPTED,
        rationale=rationale or 'Advisory was manually adopted as future planning input.',
        reason_codes=reason_codes or ['manual_adopted'],
    )


def mark_deferred(*, artifact_id: int, actor: str = 'operator-ui', rationale: str | None = None, reason_codes: list[str] | None = None) -> AdvisoryResolution:
    artifact = AdvisoryArtifact.objects.select_related('insight', 'campaign').get(pk=artifact_id)
    return _upsert_resolution(
        artifact=artifact,
        actor=actor,
        resolution_status=AdvisoryResolutionStatus.DEFERRED,
        rationale=rationale or 'Advisory was manually deferred for a later review window.',
        reason_codes=reason_codes or ['manual_deferred'],
    )


def mark_rejected(*, artifact_id: int, actor: str = 'operator-ui', rationale: str | None = None, reason_codes: list[str] | None = None) -> AdvisoryResolution:
    artifact = AdvisoryArtifact.objects.select_related('insight', 'campaign').get(pk=artifact_id)
    return _upsert_resolution(
        artifact=artifact,
        actor=actor,
        resolution_status=AdvisoryResolutionStatus.REJECTED,
        rationale=rationale or 'Advisory was manually rejected after governance review.',
        reason_codes=reason_codes or ['manual_rejected'],
    )

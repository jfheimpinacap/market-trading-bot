from __future__ import annotations

from apps.certification_board.models import (
    DownstreamOutcomeReference,
    DownstreamOutcomeReferenceStatus,
    DownstreamOutcomeReferenceType,
    ResponseCaseResolution,
)


def ensure_reference_for_resolution(*, resolution: ResponseCaseResolution) -> DownstreamOutcomeReference:
    existing = resolution.downstream_references.order_by('-created_at', '-id').first()
    if existing is not None:
        return existing

    outcome = resolution.linked_candidate.latest_lifecycle_outcome if resolution.linked_candidate else None
    reference_id = (outcome.linked_target_reference if outcome else '') or ''
    reference_type = DownstreamOutcomeReferenceType.MANUAL_NOTE
    status = DownstreamOutcomeReferenceStatus.MISSING
    summary = 'No downstream reference linked yet.'

    if reference_id:
        lowered = reference_id.lower()
        if 'eval' in lowered or 'reeval' in lowered:
            reference_type = DownstreamOutcomeReferenceType.EVALUATION_REVIEW
        elif 'tuning' in lowered:
            reference_type = DownstreamOutcomeReferenceType.TUNING_REVIEW
        elif 'rollback' in lowered:
            reference_type = DownstreamOutcomeReferenceType.ROLLBACK_REVIEW
        elif 'monitor' in lowered:
            reference_type = DownstreamOutcomeReferenceType.MONITORING_DECISION
        else:
            reference_type = DownstreamOutcomeReferenceType.MANUAL_NOTE
        status = DownstreamOutcomeReferenceStatus.LINKED
        summary = 'Reference inferred from latest lifecycle outcome.'

    return DownstreamOutcomeReference.objects.create(
        linked_resolution=resolution,
        reference_type=reference_type,
        reference_status=status,
        downstream_reference_id=reference_id,
        downstream_reference_label=reference_id,
        summary=summary,
        metadata={'source': 'baseline-response-resolution-run'},
    )


def create_manual_reference(*, resolution: ResponseCaseResolution, payload: dict) -> DownstreamOutcomeReference:
    return DownstreamOutcomeReference.objects.create(
        linked_resolution=resolution,
        reference_type=payload.get('reference_type', DownstreamOutcomeReferenceType.MANUAL_NOTE),
        reference_status=payload.get('reference_status', DownstreamOutcomeReferenceStatus.PARTIAL),
        downstream_reference_id=payload.get('downstream_reference_id', ''),
        downstream_reference_label=payload.get('downstream_reference_label', ''),
        summary=payload.get('summary', ''),
        metadata=payload.get('metadata', {}),
    )

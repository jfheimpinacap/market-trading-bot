from __future__ import annotations

from django.utils import timezone

from apps.certification_board.models import BaselineResponseCase, DownstreamAcknowledgement, ResponseReviewStageRecord


def record_review_stage(
    *,
    response_case: BaselineResponseCase,
    stage_type: str,
    stage_status: str,
    stage_notes: str = '',
    stage_actor: str = '',
    stage_at=None,
    linked_acknowledgement: DownstreamAcknowledgement | None = None,
    metadata: dict | None = None,
) -> ResponseReviewStageRecord:
    return ResponseReviewStageRecord.objects.create(
        linked_response_case=response_case,
        linked_acknowledgement=linked_acknowledgement,
        stage_type=stage_type,
        stage_status=stage_status,
        stage_notes=stage_notes,
        stage_actor=stage_actor,
        stage_at=stage_at or timezone.now(),
        metadata=metadata or {},
    )


def latest_stage_for_case(response_case: BaselineResponseCase) -> ResponseReviewStageRecord | None:
    return response_case.review_stage_records.order_by('-created_at', '-id').first()

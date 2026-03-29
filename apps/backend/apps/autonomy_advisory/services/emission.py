from __future__ import annotations

from django.utils import timezone

from apps.autonomy_advisory.models import AdvisoryArtifact, AdvisoryArtifactStatus, AdvisoryTargetScope
from apps.autonomy_advisory.services.candidates import map_target_to_artifact
from apps.memory_retrieval.models import MemoryDocument, MemoryDocumentType
from .dedup import find_duplicate_emitted_artifact


def _target_scope(recommendation_target: str) -> str:
    return {
        'memory': AdvisoryTargetScope.MEMORY,
        'roadmap': AdvisoryTargetScope.ROADMAP,
        'scenario': AdvisoryTargetScope.SCENARIO,
        'program': AdvisoryTargetScope.PROGRAM,
        'manager': AdvisoryTargetScope.MANAGER,
        'operator_review': AdvisoryTargetScope.OPERATOR_REVIEW,
    }.get(recommendation_target, AdvisoryTargetScope.OPERATOR_REVIEW)


def emit_advisory_artifact(*, insight, actor: str, advisory_run=None) -> AdvisoryArtifact:
    artifact_type = map_target_to_artifact(insight.recommendation_target)
    if not artifact_type:
        return AdvisoryArtifact.objects.create(
            advisory_run=advisory_run,
            insight=insight,
            campaign=insight.campaign,
            artifact_type='MANAGER_REVIEW_NOTE',
            artifact_status=AdvisoryArtifactStatus.BLOCKED,
            target_scope=AdvisoryTargetScope.OPERATOR_REVIEW,
            summary=f'Insight #{insight.id} requires manual advisory review',
            rationale='Recommendation target could not be mapped to an advisory artifact type.',
            reason_codes=['unsupported_recommendation_target'],
            blockers=['UNSUPPORTED_TARGET'],
            metadata={'insight_target': insight.recommendation_target},
        )

    duplicate = find_duplicate_emitted_artifact(insight_id=insight.id, artifact_type=artifact_type)
    if duplicate:
        return AdvisoryArtifact.objects.create(
            advisory_run=advisory_run,
            insight=insight,
            campaign=insight.campaign,
            artifact_type=artifact_type,
            artifact_status=AdvisoryArtifactStatus.DUPLICATE_SKIPPED,
            target_scope=_target_scope(insight.recommendation_target),
            summary=f'Duplicate skipped for insight #{insight.id}',
            rationale='Equivalent emitted advisory already exists for this insight.',
            reason_codes=['duplicate_emitted_artifact'],
            blockers=['ALREADY_EMITTED'],
            metadata={'duplicate_of_artifact_id': duplicate.id},
        )

    linked_memory_document = None
    if artifact_type == 'MEMORY_PRECEDENT_NOTE':
        linked_memory_document = MemoryDocument.objects.create(
            document_type=MemoryDocumentType.LEARNING_NOTE,
            source_app='autonomy_advisory',
            source_object_id=f'insight-{insight.id}',
            title=f'Autonomy advisory precedent from insight #{insight.id}',
            text_content=insight.summary,
            structured_summary={
                'insight_id': insight.id,
                'campaign_id': insight.campaign_id,
                'reason_codes': insight.reason_codes,
                'recommendation_target': insight.recommendation_target,
            },
            tags=['autonomy', 'advisory', 'precedent'],
            metadata={'created_by': actor},
        )

    return AdvisoryArtifact.objects.create(
        advisory_run=advisory_run,
        insight=insight,
        campaign=insight.campaign,
        artifact_type=artifact_type,
        artifact_status=AdvisoryArtifactStatus.EMITTED,
        target_scope=_target_scope(insight.recommendation_target),
        summary=insight.summary,
        rationale=insight.recommended_followup or f'Manual-first advisory emission from insight #{insight.id}.',
        reason_codes=insight.reason_codes,
        blockers=[],
        emitted_by=actor,
        emitted_at=timezone.now(),
        linked_memory_document=linked_memory_document,
        linked_feedback_artifact=f'autonomy_feedback:insight:{insight.id}' if insight.campaign_id else '',
        linked_program_note=f'autonomy_program:insight:{insight.id}' if insight.recommendation_target in {'program', 'manager'} else '',
        metadata={'insight_metadata': insight.metadata, 'recommendation_target': insight.recommendation_target},
    )

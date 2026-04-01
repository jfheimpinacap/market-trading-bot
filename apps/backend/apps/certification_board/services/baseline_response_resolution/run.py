from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.certification_board.models import (
    BaselineResponseCase,
    BaselineResponseLifecycleRun,
    BaselineResponseResolutionRun,
    ResponseCaseResolution,
    ResponseCaseResolutionStatus,
    ResponseCaseResolutionType,
    ResponseResolutionProgressStatus,
)
from apps.certification_board.services.baseline_response_resolution.candidate_building import build_resolution_candidate
from apps.certification_board.services.baseline_response_resolution.recommendation import build_resolution_recommendation
from apps.certification_board.services.baseline_response_resolution.references import ensure_reference_for_resolution
from apps.certification_board.services.baseline_response_resolution.resolution import upsert_proposed_resolution


@transaction.atomic
def run_baseline_response_resolution(*, actor: str = 'operator-ui', metadata: dict | None = None) -> dict:
    run = BaselineResponseResolutionRun.objects.create(
        started_at=timezone.now(),
        linked_baseline_response_lifecycle_run=BaselineResponseLifecycleRun.objects.order_by('-started_at', '-id').first(),
        metadata={'actor': actor, 'manual_first': True, 'paper_only': True, **(metadata or {})},
    )

    cases = list(BaselineResponseCase.objects.all().order_by('-created_at', '-id')[:500])
    candidates = []
    resolutions = []
    recommendations = []

    for response_case in cases:
        candidate = build_resolution_candidate(run=run, response_case=response_case)
        resolution = upsert_proposed_resolution(candidate=candidate)
        reference = ensure_reference_for_resolution(resolution=resolution)
        recommendation = build_resolution_recommendation(run=run, candidate=candidate, resolution=resolution, reference=reference)
        candidates.append(candidate)
        resolutions.append(resolution)
        recommendations.append(recommendation)

    progress_counter = Counter(item.downstream_progress_status for item in candidates)
    resolution_type_counter = Counter(item.resolution_type for item in resolutions)

    run.completed_at = timezone.now()
    run.candidate_count = len(candidates)
    run.ready_to_close_count = progress_counter.get(ResponseResolutionProgressStatus.READY_TO_RESOLVE, 0)
    run.resolved_count = ResponseCaseResolution.objects.filter(resolution_status=ResponseCaseResolutionStatus.RESOLVED).count()
    run.waiting_evidence_count = progress_counter.get(ResponseResolutionProgressStatus.WAITING_EVIDENCE, 0)
    run.closed_no_action_count = resolution_type_counter.get(ResponseCaseResolutionType.CLOSED_NO_ACTION, 0)
    run.escalated_count = resolution_type_counter.get(ResponseCaseResolutionType.ESCALATED_FOR_MANUAL_REVIEW, 0)
    run.recommendation_summary = dict(Counter(item.recommendation_type for item in recommendations))
    run.save(
        update_fields=[
            'completed_at',
            'candidate_count',
            'ready_to_close_count',
            'resolved_count',
            'waiting_evidence_count',
            'closed_no_action_count',
            'escalated_count',
            'recommendation_summary',
            'updated_at',
        ]
    )

    return {'run': run, 'candidates': candidates, 'resolutions': resolutions, 'recommendations': recommendations}


def build_response_resolution_summary() -> dict:
    latest_run = BaselineResponseResolutionRun.objects.order_by('-started_at', '-id').first()
    resolutions = ResponseCaseResolution.objects.all()
    return {
        'latest_run': latest_run,
        'tracked_open_cases': BaselineResponseCase.objects.exclude(case_status='CLOSED_NO_ACTION').count(),
        'total_candidates': latest_run.candidate_count if latest_run else 0,
        'ready_to_resolve': latest_run.ready_to_close_count if latest_run else 0,
        'waiting_evidence': latest_run.waiting_evidence_count if latest_run else 0,
        'resolved': resolutions.filter(resolution_status=ResponseCaseResolutionStatus.RESOLVED).count(),
        'escalated': resolutions.filter(resolution_status=ResponseCaseResolutionStatus.ESCALATED).count(),
        'closed_no_action': resolutions.filter(resolution_type=ResponseCaseResolutionType.CLOSED_NO_ACTION).count(),
        'deferred': resolutions.filter(resolution_status=ResponseCaseResolutionStatus.DEFERRED).count(),
        'resolution_type_summary': dict(Counter(resolutions.values_list('resolution_type', flat=True))),
        'recommendation_summary': latest_run.recommendation_summary if latest_run else {},
    }

from __future__ import annotations

from apps.certification_board.models import (
    DownstreamOutcomeReferenceStatus,
    ResponseCaseResolutionStatus,
    ResponseCaseResolutionType,
    ResponseResolutionRecommendation,
    ResponseResolutionRecommendationType,
)


def build_resolution_recommendation(*, run, candidate, resolution, reference):
    if resolution.resolution_type == ResponseCaseResolutionType.CLOSED_NO_ACTION:
        recommendation_type = ResponseResolutionRecommendationType.CLOSE_CASE_NO_ACTION
        rationale = 'Downstream lifecycle indicates no further action; case can be manually closed.'
        reason_codes = ['no_action_required']
        blockers = []
        confidence = '0.9000'
    elif resolution.resolution_status == ResponseCaseResolutionStatus.READY_TO_CLOSE and reference.reference_status == DownstreamOutcomeReferenceStatus.MISSING:
        recommendation_type = ResponseResolutionRecommendationType.REQUIRE_DOWNSTREAM_REFERENCE
        rationale = 'Case appears resolvable but needs explicit downstream reference before closure.'
        reason_codes = ['missing_reference']
        blockers = ['reference_required']
        confidence = '0.8200'
    elif resolution.resolution_status == ResponseCaseResolutionStatus.READY_TO_CLOSE:
        recommendation_type = ResponseResolutionRecommendationType.CLOSE_CASE_AS_RESOLVED
        rationale = 'Case has sufficient downstream evidence and is ready for manual close.'
        reason_codes = ['ready_to_close']
        blockers = []
        confidence = '0.9000'
    elif candidate.downstream_progress_status == 'WAITING_EVIDENCE':
        recommendation_type = ResponseResolutionRecommendationType.KEEP_WAITING_FOR_EVIDENCE
        rationale = 'Downstream progress is waiting evidence; keep case open until evidence arrives.'
        reason_codes = ['waiting_evidence']
        blockers = ['insufficient_evidence']
        confidence = '0.8500'
    elif resolution.resolution_type == ResponseCaseResolutionType.ESCALATED_FOR_MANUAL_REVIEW:
        recommendation_type = ResponseResolutionRecommendationType.ESCALATE_FOR_MANUAL_REVIEW
        rationale = 'Case is ambiguous and requires explicit manual intervention.'
        reason_codes = ['manual_review_required']
        blockers = resolution.blockers
        confidence = '0.7500'
    else:
        recommendation_type = ResponseResolutionRecommendationType.REORDER_CASE_RESOLUTION_PRIORITY
        rationale = 'Case should be reprioritized pending clearer downstream outcome.'
        reason_codes = ['reprioritize']
        blockers = resolution.blockers
        confidence = '0.6000'

    return ResponseResolutionRecommendation.objects.create(
        resolution_run=run,
        target_resolution=resolution,
        target_case=candidate.linked_response_case,
        recommendation_type=recommendation_type,
        rationale=rationale,
        reason_codes=reason_codes,
        blockers=blockers,
        confidence=confidence,
        metadata={'source': 'baseline-response-resolution-run'},
    )

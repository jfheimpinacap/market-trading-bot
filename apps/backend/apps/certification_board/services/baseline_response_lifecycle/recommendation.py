from __future__ import annotations

from decimal import Decimal

from apps.certification_board.models import (
    BaselineResponseCase,
    BaselineResponseLifecycleRun,
    DownstreamAcknowledgement,
    DownstreamAcknowledgementStatus,
    DownstreamLifecycleOutcome,
    DownstreamLifecycleOutcomeType,
    ResponseLifecycleRecommendation,
    ResponseLifecycleRecommendationType,
)


def build_lifecycle_recommendation(
    *,
    lifecycle_run: BaselineResponseLifecycleRun,
    response_case: BaselineResponseCase,
    acknowledgement: DownstreamAcknowledgement | None,
    outcome: DownstreamLifecycleOutcome | None,
) -> ResponseLifecycleRecommendation:
    recommendation_type = ResponseLifecycleRecommendationType.REQUEST_ACKNOWLEDGEMENT_UPDATE
    rationale = 'No downstream acknowledgement has been recorded yet for this routed response case.'
    reason_codes = ['ACK_MISSING']
    blockers: list[str] = []
    confidence = Decimal('0.6000')

    if acknowledgement and acknowledgement.acknowledgement_status == DownstreamAcknowledgementStatus.ACCEPTED_FOR_REVIEW:
        recommendation_type = ResponseLifecycleRecommendationType.MARK_ACCEPTED_FOR_REVIEW
        rationale = 'Downstream target accepted the case for review; continue stage-level lifecycle tracking.'
        reason_codes = ['DOWNSTREAM_ACCEPTED']
        confidence = Decimal('0.8200')
    elif acknowledgement and acknowledgement.acknowledgement_status == DownstreamAcknowledgementStatus.WAITING_MORE_EVIDENCE:
        recommendation_type = ResponseLifecycleRecommendationType.RECORD_WAITING_EVIDENCE
        rationale = 'Downstream target requested more evidence; keep case open and prioritize evidence collection stage.'
        reason_codes = ['WAITING_EVIDENCE']
        blockers = ['evidence_gap']
        confidence = Decimal('0.8400')
    elif acknowledgement and acknowledgement.acknowledgement_status == DownstreamAcknowledgementStatus.REJECTED_BY_TARGET:
        recommendation_type = ResponseLifecycleRecommendationType.RECORD_REJECTED_BY_TARGET
        rationale = 'Downstream target rejected this case; preserve lineage and prepare manual follow-up or closure.'
        reason_codes = ['DOWNSTREAM_REJECTED']
        blockers = ['target_rejection']
        confidence = Decimal('0.9000')
    elif outcome and outcome.outcome_type == DownstreamLifecycleOutcomeType.RESOLVED_BY_TARGET:
        recommendation_type = ResponseLifecycleRecommendationType.PREPARE_CASE_RESOLUTION
        rationale = 'Downstream lifecycle indicates resolution. Prepare manual case resolution in the next governance step.'
        reason_codes = ['RESOLUTION_SIGNAL_READY']
        confidence = Decimal('0.8800')
    elif outcome and outcome.outcome_type in {DownstreamLifecycleOutcomeType.ESCALATED_BACK, DownstreamLifecycleOutcomeType.STILL_UNDER_REVIEW}:
        recommendation_type = ResponseLifecycleRecommendationType.ESCALATE_FOR_FOLLOWUP
        rationale = 'Case remains without a firm downstream outcome; escalate manual follow-up for acknowledgement progress.'
        reason_codes = ['FOLLOWUP_REQUIRED']
        blockers = ['downstream_response_delay']
        confidence = Decimal('0.7600')

    return ResponseLifecycleRecommendation.objects.create(
        lifecycle_run=lifecycle_run,
        target_case=response_case,
        recommendation_type=recommendation_type,
        rationale=rationale,
        reason_codes=reason_codes,
        confidence=confidence,
        blockers=blockers,
        metadata={'manual_first': True, 'paper_only': True},
    )

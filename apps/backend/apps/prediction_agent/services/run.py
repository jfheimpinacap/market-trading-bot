from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.prediction_agent.models import (
    PredictionConvictionReviewStatus,
    PredictionIntakeRun,
    PredictionIntakeStatus,
    PredictionRuntimeAssessment,
    PredictionRuntimeRecommendation,
    PredictionRuntimeRecommendationType,
    PredictionRuntimeRun,
    RiskReadyPredictionHandoffStatus,
)
from apps.prediction_agent.services.calibration import q4, runtime_calibrated_probability, runtime_confidence_uncertainty
from apps.prediction_agent.services.candidate_building import build_runtime_candidates
from apps.prediction_agent.services.context_adjustment import apply_context_adjustment
from apps.prediction_agent.services.conviction import review_candidate
from apps.prediction_agent.services.features import build_prediction_features
from apps.prediction_agent.services.intake import build_intake_candidates
from apps.prediction_agent.services.model_runtime import resolve_runtime_probability
from apps.prediction_agent.services.recommendation import build_recommendation, create_intake_recommendation, resolve_prediction_status
from apps.prediction_agent.services.risk_handoff import build_risk_ready_handoff
from apps.prediction_training.services.registry import get_active_model_artifact


@dataclass
class IntakeRunResult:
    intake_run: PredictionIntakeRun


@dataclass
class RuntimeReviewResult:
    runtime_run: PredictionRuntimeRun


def _safe_decimal(value: Decimal | None, default: str = '0.0000') -> Decimal:
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


def _to_score(value: Decimal | None, default: str = '0.5000') -> Decimal:
    return max(Decimal('0.0001'), min(Decimal('0.9999'), _safe_decimal(value, default)))


@transaction.atomic
def run_prediction_intake_review(*, triggered_by: str = 'manual') -> IntakeRunResult:
    intake_run = PredictionIntakeRun.objects.create(started_at=timezone.now(), metadata={'triggered_by': triggered_by})
    intake_result = build_intake_candidates(intake_run=intake_run)

    reviews = []
    handoffs = []
    recommendation_counter: Counter[str] = Counter()

    for candidate in intake_result.candidates:
        if candidate.intake_status != PredictionIntakeStatus.READY_FOR_RUNTIME:
            continue
        review = review_candidate(intake_candidate=candidate)
        handoff = build_risk_ready_handoff(review=review)
        recommendation = create_intake_recommendation(intake_run=intake_run, review=review, handoff=handoff)
        recommendation_counter[recommendation.recommendation_type] += 1
        reviews.append(review)
        handoffs.append(handoff)

    intake_run.completed_at = timezone.now()
    intake_run.considered_handoff_count = intake_result.considered_count
    intake_run.runtime_candidate_count = intake_result.runtime_ready_count
    intake_run.risk_ready_count = sum(1 for item in handoffs if item.handoff_status == RiskReadyPredictionHandoffStatus.READY)
    intake_run.monitoring_only_count = sum(1 for item in reviews if item.review_status == PredictionConvictionReviewStatus.KEEP_FOR_MONITORING)
    intake_run.ignored_no_edge_count = sum(1 for item in reviews if item.review_status == PredictionConvictionReviewStatus.IGNORE_NO_EDGE)
    intake_run.ignored_low_confidence_count = sum(1 for item in reviews if item.review_status == PredictionConvictionReviewStatus.IGNORE_LOW_CONFIDENCE)
    intake_run.manual_review_count = sum(1 for item in reviews if item.review_status == PredictionConvictionReviewStatus.REQUIRE_MANUAL_PREDICTION_REVIEW)
    intake_run.recommendation_summary = dict(recommendation_counter)
    intake_run.save()
    return IntakeRunResult(intake_run=intake_run)


@transaction.atomic
def run_prediction_runtime_review(*, triggered_by: str = 'manual') -> RuntimeReviewResult:
    started_at = timezone.now()
    active_artifact = get_active_model_artifact()
    runtime_run = PredictionRuntimeRun.objects.create(
        started_at=started_at,
        active_model_context={
            'active_model_id': active_artifact.id if active_artifact else None,
            'active_model_name': active_artifact.name if active_artifact else '',
            'active_model_version': active_artifact.version if active_artifact else '',
            'fallback_mode': 'heuristic_conservative',
            'calibration_mode': 'runtime_center_pull',
        },
        metadata={'triggered_by': triggered_by},
    )

    candidate_result = build_runtime_candidates(runtime_run=runtime_run)
    recommendation_counter: Counter[str] = Counter()

    scored_count = 0
    high_edge_count = 0
    low_confidence_count = 0
    sent_to_risk_count = 0
    sent_to_signal_fusion_count = 0

    for candidate in candidate_result.candidates:
        feature_result = build_prediction_features(market=candidate.linked_market)
        feature_summary = feature_result.snapshot or {}

        market_probability = _to_score(candidate.market_probability)
        narrative_support = _to_score(candidate.narrative_support_score)
        divergence_score = _to_score(candidate.divergence_score, '0.0000')
        evidence_quality_score = _to_score(candidate.candidate_quality_score)

        runtime_model = resolve_runtime_probability(
            market_probability=market_probability,
            narrative_support_score=narrative_support,
            divergence_score=divergence_score,
            candidate_quality_score=evidence_quality_score,
            feature_summary=feature_summary,
        )

        provisional_edge = q4(runtime_model.system_probability - market_probability)

        context_result = apply_context_adjustment(
            market_id=candidate.linked_market_id,
            market_probability=market_probability,
            calibrated_probability=runtime_model.system_probability,
            narrative_support_score=narrative_support,
            divergence_score=divergence_score,
        )

        confidence_score, uncertainty_score = runtime_confidence_uncertainty(
            edge=provisional_edge,
            evidence_quality_score=evidence_quality_score,
            precedent_caution_score=context_result.precedent_caution_score,
            signal_conflict_score=context_result.signal_conflict_score,
        )

        calibrated_probability = runtime_calibrated_probability(
            system_probability=runtime_model.system_probability,
            evidence_quality_score=evidence_quality_score,
            uncertainty_score=uncertainty_score,
        )
        raw_edge = q4(calibrated_probability - market_probability)
        adjusted_edge = q4(raw_edge + context_result.narrative_influence_score - (context_result.precedent_caution_score * Decimal('0.25')))

        prediction_status = resolve_prediction_status(
            adjusted_edge=adjusted_edge,
            confidence_score=confidence_score,
            evidence_quality_score=evidence_quality_score,
            signal_conflict_score=context_result.signal_conflict_score,
        )

        reason_codes = [
            *runtime_model.reason_codes,
            *context_result.reason_codes,
            f'MODE:{runtime_model.model_mode}',
        ]

        assessment = PredictionRuntimeAssessment.objects.create(
            linked_candidate=candidate,
            active_model_name=runtime_model.active_model_name,
            model_mode=runtime_model.model_mode,
            system_probability=runtime_model.system_probability,
            calibrated_probability=calibrated_probability,
            market_probability=market_probability,
            raw_edge=raw_edge,
            adjusted_edge=adjusted_edge,
            confidence_score=confidence_score,
            uncertainty_score=uncertainty_score,
            evidence_quality_score=evidence_quality_score,
            precedent_caution_score=context_result.precedent_caution_score,
            narrative_influence_score=context_result.narrative_influence_score,
            prediction_status=prediction_status,
            rationale=(
                f'Runtime review: model_mode={runtime_model.model_mode}, raw_edge={raw_edge}, adjusted_edge={adjusted_edge}, '
                f'confidence={confidence_score}, uncertainty={uncertainty_score}.'
            ),
            reason_codes=reason_codes,
            feature_summary=feature_summary,
            metadata={
                'model_runtime': runtime_model.metadata,
                'context_adjustment': context_result.metadata,
                'stale_market_data': feature_result.stale_market_data,
            },
        )

        recommendation_type, rec_reason_codes, rec_confidence, blockers, rationale = build_recommendation(assessment)
        PredictionRuntimeRecommendation.objects.create(
            runtime_run=runtime_run,
            target_assessment=assessment,
            recommendation_type=recommendation_type,
            rationale=rationale,
            reason_codes=rec_reason_codes,
            confidence=rec_confidence,
            blockers=blockers,
        )

        recommendation_counter[recommendation_type] += 1
        scored_count += 1
        if abs(adjusted_edge) >= Decimal('0.0800'):
            high_edge_count += 1
        if confidence_score < Decimal('0.4200'):
            low_confidence_count += 1
        if recommendation_type == PredictionRuntimeRecommendationType.SEND_TO_RISK_ASSESSMENT:
            sent_to_risk_count += 1
        if recommendation_type == PredictionRuntimeRecommendationType.SEND_TO_SIGNAL_FUSION:
            sent_to_signal_fusion_count += 1

    runtime_run.completed_at = timezone.now()
    runtime_run.candidate_count = len(candidate_result.candidates)
    runtime_run.scored_count = scored_count
    runtime_run.blocked_count = candidate_result.blocked_count
    runtime_run.high_edge_count = high_edge_count
    runtime_run.low_confidence_count = low_confidence_count
    runtime_run.sent_to_risk_count = sent_to_risk_count
    runtime_run.sent_to_signal_fusion_count = sent_to_signal_fusion_count
    runtime_run.recommendation_summary = dict(recommendation_counter)
    runtime_run.save()

    return RuntimeReviewResult(runtime_run=runtime_run)

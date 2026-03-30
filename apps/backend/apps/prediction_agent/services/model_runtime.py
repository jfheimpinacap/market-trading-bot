from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.prediction_agent.models import PredictionRuntimeModelMode
from apps.prediction_agent.services.calibration import clamp_probability
from apps.prediction_training.services.dataset import FEATURE_COLUMNS
from apps.prediction_training.services.registry import get_active_model_artifact, predict_probability


@dataclass
class ModelRuntimeResult:
    system_probability: Decimal
    heuristic_probability: Decimal
    active_model_name: str
    model_mode: str
    reason_codes: list[str]
    metadata: dict


def _heuristic_probability(*, market_probability: Decimal, narrative_support_score: Decimal, divergence_score: Decimal, candidate_quality_score: Decimal) -> Decimal:
    baseline = market_probability
    baseline += (narrative_support_score - Decimal('0.5000')) * Decimal('0.16')
    baseline += divergence_score * Decimal('0.12')
    baseline += (candidate_quality_score - Decimal('0.5000')) * Decimal('0.08')
    return clamp_probability(baseline)


def _build_feature_vector(feature_summary: dict) -> list[float]:
    return [float(feature_summary.get(column, 0.0) or 0.0) for column in FEATURE_COLUMNS]


def resolve_runtime_probability(*, market_probability: Decimal, narrative_support_score: Decimal, divergence_score: Decimal, candidate_quality_score: Decimal, feature_summary: dict) -> ModelRuntimeResult:
    reason_codes: list[str] = []
    heuristic_probability = _heuristic_probability(
        market_probability=market_probability,
        narrative_support_score=narrative_support_score,
        divergence_score=divergence_score,
        candidate_quality_score=candidate_quality_score,
    )
    active_artifact = get_active_model_artifact()
    if active_artifact is None:
        reason_codes.append('MODEL_UNAVAILABLE_HEURISTIC_FALLBACK')
        return ModelRuntimeResult(
            system_probability=heuristic_probability,
            heuristic_probability=heuristic_probability,
            active_model_name='',
            model_mode=PredictionRuntimeModelMode.HEURISTIC_ONLY,
            reason_codes=reason_codes,
            metadata={'runtime_mode': 'heuristic_only'},
        )

    try:
        prediction = predict_probability(artifact=active_artifact, features=_build_feature_vector(feature_summary))
        model_probability = clamp_probability(prediction.probability)
    except Exception as exc:
        reason_codes.append('MODEL_RUNTIME_ERROR_HEURISTIC_FALLBACK')
        return ModelRuntimeResult(
            system_probability=heuristic_probability,
            heuristic_probability=heuristic_probability,
            active_model_name=active_artifact.name,
            model_mode=PredictionRuntimeModelMode.MODEL_WITH_HEURISTIC_FALLBACK,
            reason_codes=reason_codes,
            metadata={'runtime_mode': 'model_error_fallback', 'error': str(exc)},
        )

    evidence_weak = candidate_quality_score < Decimal('0.3500')
    if evidence_weak:
        blended_probability = clamp_probability((model_probability * Decimal('0.65')) + (heuristic_probability * Decimal('0.35')))
        reason_codes.append('LOW_EVIDENCE_BLEND_WITH_HEURISTIC')
        return ModelRuntimeResult(
            system_probability=blended_probability,
            heuristic_probability=heuristic_probability,
            active_model_name=active_artifact.name,
            model_mode=PredictionRuntimeModelMode.BLENDED,
            reason_codes=reason_codes,
            metadata={'runtime_mode': 'blended_low_evidence', 'model_probability': str(model_probability)},
        )

    return ModelRuntimeResult(
        system_probability=model_probability,
        heuristic_probability=heuristic_probability,
        active_model_name=active_artifact.name,
        model_mode=PredictionRuntimeModelMode.MODEL_ONLY,
        reason_codes=reason_codes,
        metadata={'runtime_mode': 'model_only', 'model_probability': str(model_probability)},
    )

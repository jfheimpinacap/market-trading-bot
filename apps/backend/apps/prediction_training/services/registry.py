from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from apps.prediction_training.models import PredictionModelArtifact


@dataclass
class CalibratedPrediction:
    probability: Decimal
    artifact: PredictionModelArtifact


@lru_cache(maxsize=4)
def _load_model_pair(artifact_id: int):
    artifact = PredictionModelArtifact.objects.filter(id=artifact_id).first()
    if artifact is None:
        return None, None, None
    import joblib

    model = joblib.load(Path(artifact.artifact_path))
    calibrator = joblib.load(Path(artifact.calibrator_path)) if artifact.calibrator_path else None
    return artifact, model, calibrator


def clear_model_cache() -> None:
    _load_model_pair.cache_clear()


def get_active_model_artifact() -> PredictionModelArtifact | None:
    return PredictionModelArtifact.objects.filter(is_active=True).order_by('-created_at', '-id').first()


def activate_model(*, artifact: PredictionModelArtifact) -> PredictionModelArtifact:
    PredictionModelArtifact.objects.filter(is_active=True).exclude(id=artifact.id).update(is_active=False)
    artifact.is_active = True
    artifact.save(update_fields=['is_active', 'updated_at'])
    clear_model_cache()
    return artifact


def predict_probability(*, artifact: PredictionModelArtifact, features: list[float]) -> CalibratedPrediction:
    _, model, calibrator = _load_model_pair(artifact.id)
    if model is None:
        raise RuntimeError('Model unavailable.')

    if calibrator is not None:
        probability = float(calibrator.predict_proba([features])[0][1])
    else:
        probability = float(model.predict_proba([features])[0][1])
    return CalibratedPrediction(probability=Decimal(str(round(probability, 4))), artifact=artifact)

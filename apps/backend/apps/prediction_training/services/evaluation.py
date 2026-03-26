from __future__ import annotations

from dataclasses import dataclass

from apps.prediction_training.models import ModelEvaluationProfile

DEFAULT_EVALUATION_PROFILES = [
    {
        'slug': 'conservative_model_eval',
        'name': 'Conservative model eval',
        'description': 'Prioritizes stability and calibration before any activation recommendation.',
        'config': {
            'minimum_coverage': 0.75,
            'max_failures_ratio': 0.05,
            'activation_min_score_delta': 0.08,
            'weights': {
                'accuracy': 0.20,
                'log_loss': 0.25,
                'brier_score': 0.20,
                'calibration_error': 0.20,
                'edge_hit_rate': 0.10,
                'confidence_usefulness': 0.05,
            },
        },
    },
    {
        'slug': 'balanced_model_eval',
        'name': 'Balanced model eval',
        'description': 'Balanced profile for local governance of heuristic vs trained model candidates.',
        'config': {
            'minimum_coverage': 0.60,
            'max_failures_ratio': 0.10,
            'activation_min_score_delta': 0.03,
            'weights': {
                'accuracy': 0.20,
                'log_loss': 0.20,
                'brier_score': 0.20,
                'calibration_error': 0.15,
                'edge_hit_rate': 0.15,
                'confidence_usefulness': 0.10,
            },
        },
    },
    {
        'slug': 'strict_calibration_eval',
        'name': 'Strict calibration eval',
        'description': 'Strongly penalizes miscalibration and poor reliability.',
        'config': {
            'minimum_coverage': 0.55,
            'max_failures_ratio': 0.12,
            'activation_min_score_delta': 0.02,
            'weights': {
                'accuracy': 0.10,
                'log_loss': 0.25,
                'brier_score': 0.20,
                'calibration_error': 0.30,
                'edge_hit_rate': 0.10,
                'confidence_usefulness': 0.05,
            },
        },
    },
]


@dataclass
class EvaluationProfileConfig:
    profile: ModelEvaluationProfile
    config: dict


def ensure_default_evaluation_profiles() -> None:
    for profile in DEFAULT_EVALUATION_PROFILES:
        ModelEvaluationProfile.objects.update_or_create(slug=profile['slug'], defaults=profile)


def get_evaluation_profile(slug: str | None = None) -> EvaluationProfileConfig:
    ensure_default_evaluation_profiles()
    if slug:
        profile = ModelEvaluationProfile.objects.get(slug=slug)
    else:
        profile = ModelEvaluationProfile.objects.filter(is_active=True).order_by('slug').first() or ModelEvaluationProfile.objects.order_by('slug').first()
    return EvaluationProfileConfig(profile=profile, config=profile.config or {})

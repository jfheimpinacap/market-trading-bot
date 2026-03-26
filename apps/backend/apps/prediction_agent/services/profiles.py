from __future__ import annotations

from decimal import Decimal

from apps.prediction_agent.models import PredictionModelProfile

DEFAULT_PROFILES = [
    {
        'slug': 'heuristic_baseline',
        'name': 'Heuristic Baseline',
        'description': 'Balanced linear heuristic over market baseline, momentum, narrative and learning adjustments.',
        'use_narrative': True,
        'use_learning': True,
        'calibration_alpha': Decimal('1.0500'),
        'calibration_beta': Decimal('0.0000'),
        'weights': {
            'market_anchor': 0.55,
            'momentum': 0.20,
            'narrative': 0.15,
            'relevance': 0.05,
            'learning': 0.05,
        },
    },
    {
        'slug': 'narrative_weighted',
        'name': 'Narrative Weighted',
        'description': 'Increases narrative pressure/relevance contribution for research-driven setups.',
        'use_narrative': True,
        'use_learning': True,
        'calibration_alpha': Decimal('1.1000'),
        'calibration_beta': Decimal('0.0000'),
        'weights': {
            'market_anchor': 0.45,
            'momentum': 0.15,
            'narrative': 0.30,
            'relevance': 0.05,
            'learning': 0.05,
        },
    },
    {
        'slug': 'market_momentum_weighted',
        'name': 'Market Momentum Weighted',
        'description': 'Prioritizes recent market deltas while keeping narrative as secondary signal.',
        'use_narrative': True,
        'use_learning': False,
        'calibration_alpha': Decimal('1.0000'),
        'calibration_beta': Decimal('0.0000'),
        'weights': {
            'market_anchor': 0.60,
            'momentum': 0.30,
            'narrative': 0.05,
            'relevance': 0.05,
            'learning': 0.00,
        },
    },
    {
        'slug': 'future_xgboost_placeholder',
        'name': 'Future XGBoost Placeholder',
        'description': 'Contract-compatible placeholder for future trained model loading/scoring integration.',
        'use_narrative': True,
        'use_learning': True,
        'calibration_alpha': Decimal('1.0000'),
        'calibration_beta': Decimal('0.0000'),
        'weights': {
            'market_anchor': 0.50,
            'momentum': 0.20,
            'narrative': 0.20,
            'relevance': 0.05,
            'learning': 0.05,
        },
    },
]


def ensure_default_prediction_profiles() -> None:
    for profile_data in DEFAULT_PROFILES:
        PredictionModelProfile.objects.update_or_create(slug=profile_data['slug'], defaults=profile_data)


def get_prediction_profile(slug: str | None = None) -> PredictionModelProfile:
    ensure_default_prediction_profiles()
    if slug:
        return PredictionModelProfile.objects.get(slug=slug)
    return PredictionModelProfile.objects.filter(is_active=True).order_by('slug').first() or PredictionModelProfile.objects.order_by('slug').first()

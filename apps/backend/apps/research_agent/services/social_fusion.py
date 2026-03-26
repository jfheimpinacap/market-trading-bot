from __future__ import annotations

from decimal import Decimal

from apps.research_agent.models import NarrativeSourceType


def _to_decimal(value: float) -> Decimal:
    return Decimal(f'{max(0.0, min(float(value), 1.0)):.4f}')


def social_weight(*, source_type: str, hype_risk: float, noise_risk: float) -> Decimal:
    if source_type != NarrativeSourceType.REDDIT:
        return Decimal('1.0000')
    penalty = (Decimal(str(hype_risk)) + Decimal(str(noise_risk))) / Decimal('2')
    return max(Decimal('0.2000'), (Decimal('0.6500') * (Decimal('1.0000') - penalty)).quantize(Decimal('0.0001')))


def classify_source_mix(*, rss_count: int, social_count: int, convergent: bool) -> str:
    if rss_count and social_count:
        if social_count > rss_count:
            return 'social_heavy'
        return 'news_confirmed' if convergent else 'mixed'
    if social_count:
        return 'social_only'
    return 'news_only'


def normalize_social_metrics(metadata: dict) -> tuple[Decimal, Decimal, Decimal]:
    social_signal = _to_decimal(metadata.get('social_signal_strength', 0.3))
    hype_risk = _to_decimal(metadata.get('hype_risk', 0.25))
    noise_risk = _to_decimal(metadata.get('noise_risk', 0.25))
    return social_signal, hype_risk, noise_risk

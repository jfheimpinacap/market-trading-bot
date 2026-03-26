from __future__ import annotations

from decimal import Decimal

from apps.research_agent.models import NarrativeSourceType


def social_weight(*, source_type: str, hype_risk: float, noise_risk: float) -> Decimal:
    if source_type not in {NarrativeSourceType.REDDIT, NarrativeSourceType.TWITTER}:
        return Decimal('1.0000')
    baseline = Decimal('0.6500') if source_type == NarrativeSourceType.REDDIT else Decimal('0.7000')
    penalty = (Decimal(str(hype_risk)) + Decimal(str(noise_risk))) / Decimal('2')
    return max(Decimal('0.2000'), (baseline * (Decimal('1.0000') - penalty)).quantize(Decimal('0.0001')))


def classify_source_mix(*, rss_count: int, reddit_count: int, twitter_count: int, convergent: bool) -> str:
    social_count = reddit_count + twitter_count
    if rss_count and reddit_count and twitter_count and convergent:
        return 'full_signal'
    if rss_count and social_count:
        if social_count > (rss_count * 2):
            return 'social_heavy'
        return 'news_confirmed' if convergent else 'mixed'
    if social_count:
        return 'social_only'
    return 'news_only'

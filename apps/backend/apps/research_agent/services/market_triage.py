from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count
from django.utils import timezone

from apps.markets.models import Market, MarketSourceType, MarketStatus
from apps.research_agent.models import NarrativeSentiment, ResearchCandidate, ResearchFilterProfile, TriageStatus


@dataclass(frozen=True)
class TriageProfile:
    min_liquidity: Decimal
    min_volume_24h: Decimal
    min_resolution_hours: int
    max_resolution_hours: int
    stale_hours: int
    shortlist_score: Decimal
    watch_score: Decimal
    narrative_boost_weight: Decimal


PROFILES: dict[str, TriageProfile] = {
    ResearchFilterProfile.CONSERVATIVE: TriageProfile(
        min_liquidity=Decimal('50000'),
        min_volume_24h=Decimal('15000'),
        min_resolution_hours=12,
        max_resolution_hours=24 * 90,
        stale_hours=6,
        shortlist_score=Decimal('62'),
        watch_score=Decimal('45'),
        narrative_boost_weight=Decimal('12'),
    ),
    ResearchFilterProfile.BALANCED: TriageProfile(
        min_liquidity=Decimal('15000'),
        min_volume_24h=Decimal('3500'),
        min_resolution_hours=6,
        max_resolution_hours=24 * 180,
        stale_hours=12,
        shortlist_score=Decimal('55'),
        watch_score=Decimal('36'),
        narrative_boost_weight=Decimal('10'),
    ),
    ResearchFilterProfile.BROAD: TriageProfile(
        min_liquidity=Decimal('3000'),
        min_volume_24h=Decimal('500'),
        min_resolution_hours=2,
        max_resolution_hours=24 * 365,
        stale_hours=24,
        shortlist_score=Decimal('48'),
        watch_score=Decimal('28'),
        narrative_boost_weight=Decimal('8'),
    ),
}


@dataclass
class TriageInput:
    market: Market
    profile: TriageProfile
    now: timezone.datetime


@dataclass
class TriageOutcome:
    triage_status: str
    triage_score: Decimal
    exclusion_reasons: list[str]
    flags: list[str]
    rationale: str
    details: dict
    narrative_coverage: int
    narrative_relevance: Decimal
    narrative_confidence: Decimal
    narrative_direction: str
    source_mix: str
    time_to_resolution_hours: int | None


def _safe_decimal(value: Decimal | None) -> Decimal:
    return Decimal(str(value or '0'))


def resolve_profile(profile_slug: str | None) -> tuple[str, TriageProfile]:
    slug = profile_slug or ResearchFilterProfile.BALANCED
    return slug, PROFILES.get(slug, PROFILES[ResearchFilterProfile.BALANCED])


def build_market_queryset(*, provider_scope: list[str] | None = None, source_scope: list[str] | None = None):
    queryset = Market.objects.select_related('provider').filter(is_active=True)
    if provider_scope:
        queryset = queryset.filter(provider__slug__in=provider_scope)
    if source_scope:
        queryset = queryset.filter(source_type__in=source_scope)
    return queryset.order_by('-updated_at', '-id')


def _narrative_snapshot(market: Market) -> dict:
    candidate = ResearchCandidate.objects.filter(market=market).first()
    if candidate:
        metadata = candidate.metadata or {}
        confidence = Decimal(str(metadata.get('combined_confidence', '0')))
        relevance = min(Decimal('1.0'), abs(candidate.narrative_pressure))
        return {
            'coverage': int(metadata.get('linked_item_count', 0) or 0),
            'relevance': relevance.quantize(Decimal('0.0001')),
            'confidence': confidence.quantize(Decimal('0.0001')),
            'direction': candidate.sentiment_direction,
            'source_mix': candidate.source_mix,
            'cross_source_agreement': Decimal(str(metadata.get('cross_source_agreement', '0'))),
            'cross_source_divergence': Decimal(str(metadata.get('cross_source_divergence', '0'))),
        }

    aggregates = market.narrative_links.aggregate(
        coverage=Count('id'),
        avg_relevance=Avg('narrative_item__analysis__market_relevance_score'),
        avg_confidence=Avg('narrative_item__analysis__confidence'),
    )
    coverage = int(aggregates.get('coverage') or 0)
    relevance = Decimal(str(aggregates.get('avg_relevance') or '0'))
    confidence = Decimal(str(aggregates.get('avg_confidence') or '0'))
    direction = NarrativeSentiment.UNCERTAIN
    if relevance >= Decimal('0.65'):
        direction = NarrativeSentiment.BULLISH
    elif relevance <= Decimal('0.25') and coverage:
        direction = NarrativeSentiment.BEARISH
    return {
        'coverage': coverage,
        'relevance': relevance.quantize(Decimal('0.0001')),
        'confidence': confidence.quantize(Decimal('0.0001')),
        'direction': direction,
        'source_mix': 'none' if coverage == 0 else 'news_only',
        'cross_source_agreement': Decimal('0'),
        'cross_source_divergence': Decimal('0'),
    }


def evaluate_market(input_data: TriageInput) -> TriageOutcome:
    market = input_data.market
    profile = input_data.profile
    now = input_data.now

    exclusion_reasons: list[str] = []
    flags: list[str] = []

    if market.status != MarketStatus.OPEN:
        exclusion_reasons.append('market_not_open')
    if market.source_type == MarketSourceType.REAL_READ_ONLY:
        flags.append('REAL_READ_ONLY')

    liquidity = _safe_decimal(market.liquidity)
    volume_24h = _safe_decimal(market.volume_24h)
    if liquidity < profile.min_liquidity:
        exclusion_reasons.append('low_liquidity')
        flags.append('LOW_LIQUIDITY')
    else:
        flags.append('HIGH_LIQUIDITY')
    if volume_24h < profile.min_volume_24h:
        exclusion_reasons.append('low_volume')
        flags.append('LOW_VOLUME')

    resolution_hours = None
    if market.resolution_time:
        resolution_hours = int((market.resolution_time - now).total_seconds() / 3600)
        if resolution_hours < profile.min_resolution_hours:
            exclusion_reasons.append('resolution_too_close')
        if resolution_hours > profile.max_resolution_hours:
            exclusion_reasons.append('resolution_too_far')

    stale_cutoff = now - timedelta(hours=profile.stale_hours)
    if market.updated_at < stale_cutoff:
        exclusion_reasons.append('stale_market_data')
        flags.append('STALE')

    narrative = _narrative_snapshot(market)

    liquidity_component = min(liquidity / max(profile.min_liquidity, Decimal('1')), Decimal('2.0')) * Decimal('18')
    volume_component = min(volume_24h / max(profile.min_volume_24h, Decimal('1')), Decimal('2.0')) * Decimal('16')

    timing_component = Decimal('8')
    if resolution_hours is not None:
        if resolution_hours < profile.min_resolution_hours or resolution_hours > profile.max_resolution_hours:
            timing_component = Decimal('0')
        elif resolution_hours <= 72:
            timing_component = Decimal('14')
        elif resolution_hours <= 24 * 21:
            timing_component = Decimal('11')

    status_component = Decimal('14') if market.status == MarketStatus.OPEN else Decimal('0')
    freshness_component = Decimal('12') if market.updated_at >= stale_cutoff else Decimal('0')

    narrative_boost = (narrative['relevance'] * narrative['confidence'] * profile.narrative_boost_weight)
    if narrative['coverage'] and narrative_boost >= Decimal('4'):
        flags.append('NARRATIVE_BOOST')
    if narrative['cross_source_divergence'] >= Decimal('0.66'):
        exclusion_reasons.append('narrative_conflict')
        flags.append('NARRATIVE_CONFLICT')

    score = (liquidity_component + volume_component + timing_component + status_component + freshness_component + narrative_boost).quantize(Decimal('0.01'))

    if exclusion_reasons and score < profile.watch_score:
        triage_status = TriageStatus.FILTERED_OUT
    elif score >= profile.shortlist_score and not set(exclusion_reasons).intersection({'market_not_open', 'stale_market_data', 'resolution_too_close'}):
        triage_status = TriageStatus.SHORTLISTED
    elif score >= profile.watch_score:
        triage_status = TriageStatus.WATCH
    else:
        triage_status = TriageStatus.FILTERED_OUT

    rationale = (
        f"Liquidity {liquidity} / Volume24h {volume_24h}; "
        f"resolution_h={resolution_hours if resolution_hours is not None else 'n/a'}; "
        f"narrative coverage={narrative['coverage']} relevance={narrative['relevance']} confidence={narrative['confidence']}."
    )[:255]

    return TriageOutcome(
        triage_status=triage_status,
        triage_score=score,
        exclusion_reasons=exclusion_reasons,
        flags=flags,
        rationale=rationale,
        details={
            'components': {
                'liquidity': str(liquidity_component.quantize(Decimal('0.01'))),
                'volume': str(volume_component.quantize(Decimal('0.01'))),
                'timing': str(timing_component.quantize(Decimal('0.01'))),
                'status': str(status_component.quantize(Decimal('0.01'))),
                'freshness': str(freshness_component.quantize(Decimal('0.01'))),
                'narrative_boost': str(narrative_boost.quantize(Decimal('0.01'))),
            }
        },
        narrative_coverage=narrative['coverage'],
        narrative_relevance=narrative['relevance'],
        narrative_confidence=narrative['confidence'],
        narrative_direction=narrative['direction'],
        source_mix=narrative['source_mix'],
        time_to_resolution_hours=resolution_hours,
    )

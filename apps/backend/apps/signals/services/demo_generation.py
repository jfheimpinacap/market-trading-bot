from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from apps.markets.models import Market, MarketSnapshot, MarketStatus
from apps.signals.models import (
    MarketSignal,
    MarketSignalStatus,
    MarketSignalType,
    MockAgent,
    SignalDirection,
    SignalRun,
    SignalRunStatus,
)
from apps.signals.seeds import seed_mock_agents


ZERO = Decimal('0')
ONE = Decimal('1')
HUNDRED = Decimal('100')


@dataclass
class SignalDraft:
    agent: MockAgent | None
    signal_type: str
    status: str
    direction: str
    score: Decimal
    confidence: Decimal
    headline: str
    thesis: str
    rationale: str
    signal_probability: Decimal | None
    market_probability_at_signal: Decimal | None
    edge_estimate: Decimal | None
    is_actionable: bool
    expires_at: datetime | None
    metadata: dict


@dataclass
class SignalGenerationResult:
    run: SignalRun
    markets_evaluated: int
    signals_created: int
    signals_updated: int


def quantize(value: Decimal | float | int | None, places: str) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def clamp(value: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    return max(minimum, min(value, maximum))


def build_market_queryset(limit: int | None = None, market_id: int | None = None):
    queryset = Market.objects.select_related('provider', 'event').prefetch_related(
        Prefetch(
            'snapshots',
            queryset=MarketSnapshot.objects.order_by('-captured_at', '-id'),
            to_attr='signal_snapshots_cache',
        )
    ).order_by('id')
    if market_id:
        queryset = queryset.filter(pk=market_id)
    if limit:
        queryset = queryset[:limit]
    return queryset


def score_from_strength(strength: Decimal) -> Decimal:
    return clamp((strength * Decimal('100')).quantize(Decimal('0.01')), Decimal('5.00'), Decimal('97.50'))


def direction_from_edge(edge: Decimal | None) -> str:
    if edge is None:
        return SignalDirection.NEUTRAL
    if edge >= Decimal('0.0300'):
        return SignalDirection.BULLISH
    if edge <= Decimal('-0.0300'):
        return SignalDirection.BEARISH
    return SignalDirection.NEUTRAL


def build_signal_drafts(market: Market, agents_by_slug: dict[str, MockAgent]) -> list[SignalDraft]:
    snapshots = list(getattr(market, 'signal_snapshots_cache', []))[:6]
    snapshots = list(reversed(snapshots))
    latest_probability = quantize(market.current_market_probability, '0.0001')
    if latest_probability is None and snapshots:
        latest_probability = quantize(snapshots[-1].market_probability, '0.0001')
    if latest_probability is None:
        latest_probability = Decimal('0.5000')

    values = [quantize(snapshot.market_probability, '0.0001') for snapshot in snapshots if snapshot.market_probability is not None]
    values = [value for value in values if value is not None]
    baseline = latest_probability
    oldest_probability = latest_probability
    volatility = Decimal('0.0000')
    momentum = Decimal('0.0000')
    if values:
        baseline = quantize(sum(values, ZERO) / Decimal(len(values)), '0.0001') or latest_probability
        oldest_probability = values[0]
        volatility = quantize(max(values) - min(values), '0.0001') or Decimal('0.0000')
        momentum = quantize(latest_probability - oldest_probability, '0.0001') or Decimal('0.0000')

    spread_bps = market.spread_bps or 0
    spread_penalty = Decimal('0.18') if spread_bps >= 350 else Decimal('0.10') if spread_bps >= 220 else Decimal('0.00')
    liquidity = quantize(market.liquidity, '0.01') or Decimal('0.00')
    volume_24h = quantize(market.volume_24h, '0.01') or Decimal('0.00')
    is_terminal = market.status in {MarketStatus.CLOSED, MarketStatus.RESOLVED, MarketStatus.CANCELLED, MarketStatus.ARCHIVED}
    is_paused = market.status == MarketStatus.PAUSED
    is_actionable_market = market.is_active and market.status == MarketStatus.OPEN and spread_bps <= 250
    low_activity = volume_24h < Decimal('5000') or liquidity < Decimal('60000') or len(values) < 3

    heuristic_probability = clamp(
        baseline + (momentum * Decimal('0.35')) - (volatility * Decimal('0.20')),
        Decimal('0.0200'),
        Decimal('0.9800'),
    )
    edge_estimate = quantize(heuristic_probability - latest_probability, '0.0001')
    direction = direction_from_edge(edge_estimate)

    drafts: list[SignalDraft] = []
    now = timezone.now()
    base_confidence = clamp(Decimal('0.58') + (volatility * Decimal('1.4')) - spread_penalty, Decimal('0.20'), Decimal('0.92'))
    if low_activity:
        base_confidence = clamp(base_confidence - Decimal('0.18'), Decimal('0.12'), Decimal('0.92'))
    if is_paused:
        base_confidence = clamp(base_confidence - Decimal('0.12'), Decimal('0.10'), Decimal('0.92'))
    if is_terminal:
        base_confidence = Decimal('0.22')

    movement_strength = max(abs(momentum), abs(edge_estimate or Decimal('0.0000')), volatility)

    if movement_strength >= Decimal('0.0450'):
        signal_type = MarketSignalType.OPPORTUNITY if abs(edge_estimate or ZERO) >= Decimal('0.0400') else MarketSignalType.MOMENTUM
        drafts.append(
            SignalDraft(
                agent=agents_by_slug['scan-agent'],
                signal_type=signal_type,
                status=MarketSignalStatus.ACTIVE if is_actionable_market else MarketSignalStatus.MONITOR,
                direction=SignalDirection.BULLISH if momentum > 0 else SignalDirection.BEARISH if momentum < 0 else direction,
                score=score_from_strength(movement_strength + Decimal('0.08')),
                confidence=quantize(base_confidence, '0.01') or Decimal('0.50'),
                headline=f'{market.title} looks interesting after a fast local probability move',
                thesis=(
                    f'The demo scanner flagged this market because probability moved from {oldest_probability:.2%} '
                    f'to {latest_probability:.2%} across the recent local snapshot window.'
                ),
                rationale=(
                    f'Momentum={momentum:+.2%}, volatility={volatility:.2%}, spread={spread_bps} bps, '
                    f'24h volume={volume_24h:.0f}. This is a local heuristic only.'
                ),
                signal_probability=heuristic_probability,
                market_probability_at_signal=latest_probability,
                edge_estimate=edge_estimate,
                is_actionable=is_actionable_market and not low_activity,
                expires_at=now + timedelta(hours=24),
                metadata={
                    'heuristics': {
                        'baseline_probability': f'{baseline:.4f}',
                        'momentum': f'{momentum:.4f}',
                        'volatility': f'{volatility:.4f}',
                    }
                },
            )
        )

    if abs(edge_estimate or ZERO) >= Decimal('0.0350') or latest_probability >= Decimal('0.8000') or latest_probability <= Decimal('0.2000'):
        signal_type = MarketSignalType.EXTREME if latest_probability >= Decimal('0.8000') or latest_probability <= Decimal('0.2000') else MarketSignalType.MEAN_REVERSION
        drafts.append(
            SignalDraft(
                agent=agents_by_slug['prediction-agent'],
                signal_type=signal_type,
                status=MarketSignalStatus.ACTIVE if is_actionable_market else MarketSignalStatus.MONITOR,
                direction=direction,
                score=score_from_strength(max(abs(edge_estimate or ZERO), abs(latest_probability - Decimal('0.5000')))),
                confidence=quantize(clamp(base_confidence + Decimal('0.08'), Decimal('0.15'), Decimal('0.95')), '0.01') or Decimal('0.50'),
                headline='Demo probability check suggests the current price is stretched versus a local baseline',
                thesis=(
                    f'The mock prediction agent compares the market probability of {latest_probability:.2%} '
                    f'against a simple local baseline of {heuristic_probability:.2%} built from recent snapshots.'
                ),
                rationale=(
                    f'Edge estimate={edge_estimate:+.2%}. Extreme probabilities and large deviations are treated as '
                    'interesting demo opportunities, not real forecasts.'
                ),
                signal_probability=heuristic_probability,
                market_probability_at_signal=latest_probability,
                edge_estimate=edge_estimate,
                is_actionable=is_actionable_market and abs(edge_estimate or ZERO) >= Decimal('0.0400') and not low_activity,
                expires_at=now + timedelta(hours=36),
                metadata={
                    'heuristics': {
                        'heuristic_probability': f'{heuristic_probability:.4f}',
                        'market_probability': f'{latest_probability:.4f}',
                        'edge_estimate': f'{(edge_estimate or ZERO):.4f}',
                    }
                },
            )
        )

    if is_terminal or is_paused or low_activity or spread_bps >= 280:
        risk_direction = SignalDirection.NEUTRAL
        risk_status = MarketSignalStatus.MONITOR if not is_terminal else MarketSignalStatus.EXPIRED
        risk_reasons = []
        if is_terminal:
            risk_reasons.append(f'market status is {market.status.lower()}')
        if is_paused:
            risk_reasons.append('market is paused')
        if low_activity:
            risk_reasons.append('recent activity is thin')
        if spread_bps >= 280:
            risk_reasons.append(f'spread is wide at {spread_bps} bps')
        drafts.append(
            SignalDraft(
                agent=agents_by_slug['risk-agent'],
                signal_type=MarketSignalType.RISK if not low_activity else MarketSignalType.DORMANT,
                status=risk_status,
                direction=risk_direction,
                score=score_from_strength(max(volatility, Decimal('0.12'))),
                confidence=quantize(clamp(Decimal('0.72') - spread_penalty, Decimal('0.30'), Decimal('0.90')), '0.01') or Decimal('0.50'),
                headline='Demo risk review suggests reduced actionability for this market',
                thesis='The mock risk agent lowered actionability because market conditions do not look clean enough for a demo idea queue.',
                rationale='; '.join(risk_reasons) + '. This is a local-first demo safety layer, not a real risk engine.',
                signal_probability=heuristic_probability,
                market_probability_at_signal=latest_probability,
                edge_estimate=edge_estimate,
                is_actionable=False,
                expires_at=now + timedelta(hours=48),
                metadata={
                    'heuristics': {
                        'low_activity': low_activity,
                        'spread_bps': spread_bps,
                        'market_status': market.status,
                    }
                },
            )
        )

    if not drafts:
        drafts.append(
            SignalDraft(
                agent=agents_by_slug['research-agent'],
                signal_type=MarketSignalType.OPPORTUNITY,
                status=MarketSignalStatus.MONITOR,
                direction=SignalDirection.NEUTRAL,
                score=Decimal('38.00'),
                confidence=Decimal('0.34'),
                headline='Market is being monitored but does not stand out yet',
                thesis='Recent local snapshots do not show a large enough move or edge to mark this market as a stronger demo opportunity.',
                rationale='Stable recent pricing, limited edge, or mixed conditions produced a low-priority monitoring signal.',
                signal_probability=heuristic_probability,
                market_probability_at_signal=latest_probability,
                edge_estimate=edge_estimate,
                is_actionable=False,
                expires_at=now + timedelta(hours=24),
                metadata={'heuristics': {'fallback': True}},
            )
        )

    return drafts


@transaction.atomic
def generate_demo_signals(*, limit: int | None = None, market_id: int | None = None, clear_existing: bool = False) -> SignalGenerationResult:
    seed_mock_agents()
    agents_by_slug = {agent.slug: agent for agent in MockAgent.objects.filter(is_active=True)}
    run = SignalRun.objects.create(
        run_type='DEMO_SCAN',
        status=SignalRunStatus.RUNNING,
        metadata={'limit': limit, 'market_id': market_id, 'clear_existing': clear_existing},
    )

    markets = list(build_market_queryset(limit=limit, market_id=market_id))
    if clear_existing:
        MarketSignal.objects.all().delete()

    created = 0
    updated = 0

    try:
        for market in markets:
            for draft in build_signal_drafts(market, agents_by_slug):
                signal, was_created = MarketSignal.objects.update_or_create(
                    market=market,
                    agent=draft.agent,
                    signal_type=draft.signal_type,
                    status=draft.status,
                    defaults={
                        'run': run,
                        'direction': draft.direction,
                        'score': draft.score,
                        'confidence': draft.confidence,
                        'headline': draft.headline,
                        'thesis': draft.thesis,
                        'rationale': draft.rationale,
                        'signal_probability': draft.signal_probability,
                        'market_probability_at_signal': draft.market_probability_at_signal,
                        'edge_estimate': draft.edge_estimate,
                        'is_actionable': draft.is_actionable,
                        'expires_at': draft.expires_at,
                        'metadata': draft.metadata,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                    if signal.run_id != run.id:
                        signal.run = run
                        signal.save(update_fields=['run', 'updated_at'])

        run.markets_evaluated = len(markets)
        run.signals_created = created
        run.status = SignalRunStatus.COMPLETED
        run.finished_at = timezone.now()
        run.metadata = {**run.metadata, 'signals_updated': updated}
        run.save(update_fields=['markets_evaluated', 'signals_created', 'status', 'finished_at', 'metadata', 'updated_at'])
    except Exception as exc:
        run.status = SignalRunStatus.FAILED
        run.finished_at = timezone.now()
        run.notes = str(exc)
        run.save(update_fields=['status', 'finished_at', 'notes', 'updated_at'])
        raise

    return SignalGenerationResult(
        run=run,
        markets_evaluated=len(markets),
        signals_created=created,
        signals_updated=updated,
    )

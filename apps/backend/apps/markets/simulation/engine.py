from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from random import Random

from django.db import transaction
from django.utils import timezone

from apps.markets.models import Market, MarketSnapshot

from .rules import SimulationConfig, determine_next_status, movement_scale, should_skip_market
from .utils import (
    HUNDRED,
    ZERO,
    clamp_decimal,
    derive_order_book,
    derive_price_pair,
    quantize_money,
    quantize_probability,
)


@dataclass
class MarketSimulationResult:
    market_id: int
    title: str
    previous_status: str
    next_status: str
    updated: bool = False
    snapshot_created: bool = False
    skipped_reason: str | None = None
    probability_before: Decimal | None = None
    probability_after: Decimal | None = None
    state_change_reason: str | None = None


@dataclass
class SimulationBatchResult:
    processed: int = 0
    updated: int = 0
    skipped: int = 0
    snapshots_created: int = 0
    dry_run: bool = False
    state_changes: list[str] = field(default_factory=list)
    market_results: list[MarketSimulationResult] = field(default_factory=list)


class MarketSimulationEngine:
    def __init__(self, *, config: SimulationConfig | None = None, rng: Random | None = None):
        self.config = config or SimulationConfig()
        self.rng = rng or Random()

    def run_tick(self, *, markets=None, now=None, dry_run: bool = False, limit: int | None = None) -> SimulationBatchResult:
        now = now or timezone.now()
        queryset = markets if markets is not None else Market.objects.select_related('provider', 'event').order_by('id')
        selected_markets = list(queryset[:limit] if limit else queryset)
        result = SimulationBatchResult(dry_run=dry_run)

        with transaction.atomic():
            for market in selected_markets:
                market_result = self.simulate_market(market=market, now=now, dry_run=dry_run)
                result.market_results.append(market_result)
                result.processed += 1
                if market_result.skipped_reason:
                    result.skipped += 1
                    continue
                if market_result.updated:
                    result.updated += 1
                if market_result.snapshot_created:
                    result.snapshots_created += 1
                if market_result.previous_status != market_result.next_status:
                    result.state_changes.append(
                        f"{market.title}: {market_result.previous_status} -> {market_result.next_status}"
                    )
            if dry_run:
                transaction.set_rollback(True)

        return result

    def simulate_market(self, *, market: Market, now, dry_run: bool = False) -> MarketSimulationResult:
        skip_reason = should_skip_market(market, self.config)
        current_probability = quantize_probability(Decimal(str(market.current_market_probability or Decimal('0.5000'))))
        result = MarketSimulationResult(
            market_id=market.id,
            title=market.title,
            previous_status=market.status,
            next_status=market.status,
            skipped_reason=skip_reason,
            probability_before=current_probability,
            probability_after=current_probability,
        )
        if skip_reason:
            return result

        status_decision = determine_next_status(market, now, self.rng, self.config)
        next_probability = self._next_probability(market, current_probability, now)
        next_volume_24h, volume_increment = self._next_volume_values(market)
        next_volume_total = quantize_money(Decimal(str(market.volume_total or ZERO)) + volume_increment)
        next_liquidity = self._next_liquidity(market, current_probability, next_probability)
        next_spread_bps = self._next_spread_bps(market, current_probability, next_probability, status_decision.next_status)
        next_yes_price, next_no_price = derive_price_pair(next_probability)
        bid, ask, spread, last_price = derive_order_book(next_yes_price, next_spread_bps)
        open_interest = quantize_money(max(ZERO, next_liquidity * Decimal('0.36')))

        changed = any(
            [
                next_probability != current_probability,
                next_volume_24h != market.volume_24h,
                next_volume_total != market.volume_total,
                next_liquidity != market.liquidity,
                next_spread_bps != (market.spread_bps or 0),
                status_decision.next_status != market.status,
                status_decision.next_is_active != market.is_active,
            ]
        )

        if not changed:
            return result

        result.updated = True
        result.snapshot_created = True
        result.next_status = status_decision.next_status
        result.probability_after = next_probability
        result.state_change_reason = status_decision.reason

        if not dry_run:
            market.status = status_decision.next_status
            market.is_active = status_decision.next_is_active
            market.current_market_probability = next_probability
            market.current_yes_price = next_yes_price
            market.current_no_price = next_no_price
            market.liquidity = next_liquidity
            market.volume_24h = next_volume_24h
            market.volume_total = next_volume_total
            market.spread_bps = next_spread_bps
            metadata = dict(market.metadata or {})
            metadata['simulation'] = {
                'last_tick_at': now.isoformat(),
                'last_tick_status': status_decision.next_status,
                'last_state_change_reason': status_decision.reason,
            }
            market.metadata = metadata
            market.save(
                update_fields=[
                    'status',
                    'is_active',
                    'current_market_probability',
                    'current_yes_price',
                    'current_no_price',
                    'liquidity',
                    'volume_24h',
                    'volume_total',
                    'spread_bps',
                    'metadata',
                    'updated_at',
                ]
            )
            MarketSnapshot.objects.create(
                market=market,
                captured_at=now,
                market_probability=next_probability,
                yes_price=next_yes_price,
                no_price=next_no_price,
                last_price=last_price,
                bid=bid,
                ask=ask,
                spread=spread,
                liquidity=next_liquidity,
                volume=next_volume_total,
                volume_24h=next_volume_24h,
                open_interest=open_interest,
                metadata={
                    'demo': True,
                    'simulation_tick': True,
                    'status': status_decision.next_status,
                    'state_change_reason': status_decision.reason,
                },
            )

        return result

    def _next_probability(self, market: Market, current_probability: Decimal, now) -> Decimal:
        scale = movement_scale(market, now, self.config)
        centered_pull = (Decimal('0.5') - current_probability) * Decimal('0.08')
        random_component = Decimal(str(self.rng.uniform(float(-scale), float(scale))))
        drift = centered_pull + random_component
        next_probability = quantize_probability(
            clamp_decimal(
                current_probability + drift,
                self.config.probability_min,
                self.config.probability_max,
            )
        )
        return next_probability

    def _next_volume_values(self, market: Market) -> tuple[Decimal, Decimal]:
        current_volume_24h = Decimal(str(market.volume_24h or ZERO))
        current_total = Decimal(str(market.volume_total or ZERO))
        decay_ratio = Decimal(str(self.rng.uniform(
            float(self.config.volume_24h_decay_floor),
            float(self.config.volume_24h_decay_ceiling),
        )))
        decayed_volume_24h = current_volume_24h * decay_ratio
        traded_notional = current_total * Decimal(str(self.rng.uniform(0.0015, float(self.config.volume_24h_growth_ratio))))
        volume_increment = quantize_money(max(ZERO, traded_notional))
        next_volume_24h = quantize_money(max(ZERO, decayed_volume_24h + volume_increment))
        return next_volume_24h, volume_increment

    def _next_liquidity(self, market: Market, current_probability: Decimal, next_probability: Decimal) -> Decimal:
        current_liquidity = Decimal(str(market.liquidity or ZERO))
        probability_jump = abs(next_probability - current_probability)
        shift_ratio = Decimal(str(self.rng.uniform(
            float(-self.config.liquidity_shift_ratio),
            float(self.config.liquidity_shift_ratio),
        )))
        directional_adjustment = Decimal('1') + shift_ratio - (probability_jump * Decimal('3.2'))
        next_liquidity = quantize_money(max(self.config.liquidity_min, current_liquidity * directional_adjustment))
        return next_liquidity

    def _next_spread_bps(self, market: Market, current_probability: Decimal, next_probability: Decimal, status: str) -> int:
        base_spread = market.spread_bps or self.config.min_spread_bps
        movement_penalty = int(abs(next_probability - current_probability) * HUNDRED * Decimal('12'))
        random_adjustment = self.rng.randint(-20, 24)
        if status == 'paused':
            random_adjustment += 35
        if status == 'closed':
            random_adjustment -= 30
        spread_bps = base_spread + movement_penalty + random_adjustment
        return max(self.config.min_spread_bps, min(self.config.max_spread_bps, spread_bps))

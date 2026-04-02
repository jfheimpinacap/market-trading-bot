from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from apps.autonomous_trader.models import AutonomousDispatchRecord
from apps.markets.models import Market
from apps.mission_control.models import AutonomousRuntimeSession, AutonomousSessionAdmissionDecision
from apps.paper_trading.models import PaperPosition, PaperPositionStatus
from apps.portfolio_governor.models import (
    PortfolioExposureClusterSnapshot,
    PortfolioExposureClusterType,
    PortfolioExposureConcentrationStatus,
    PortfolioExposureCoordinationRun,
    PortfolioExposureNetDirection,
    PortfolioExposureRiskPressureState,
    SessionExposureContribution,
    SessionExposureContributionDirection,
    SessionExposureContributionRole,
    SessionExposureContributionStrength,
)

PENDING_DISPATCH_STATUSES = ['QUEUED', 'DISPATCHED', 'PARTIAL']
ACTIVE_SESSION_STATUSES = ['RUNNING', 'DEGRADED', 'PAUSED']


def _direction_from_side(side: str) -> str:
    if side == 'YES':
        return 'LONG'
    if side == 'NO':
        return 'SHORT'
    return 'NEUTRAL'


def _aggregate_net_direction(counts: dict[str, int]) -> str:
    long_count = counts.get('LONG', 0)
    short_count = counts.get('SHORT', 0)
    if long_count > short_count:
        return PortfolioExposureNetDirection.LONG_BIAS
    if short_count > long_count:
        return PortfolioExposureNetDirection.SHORT_BIAS
    if long_count + short_count == 0:
        return PortfolioExposureNetDirection.UNCLEAR
    return PortfolioExposureNetDirection.MIXED


def _concentration_status(session_count: int, pending_dispatch_count: int, open_position_count: int) -> str:
    pressure = session_count + pending_dispatch_count + open_position_count
    if pressure >= 8:
        return PortfolioExposureConcentrationStatus.CRITICAL
    if pressure >= 6:
        return PortfolioExposureConcentrationStatus.HIGH
    if pressure >= 4:
        return PortfolioExposureConcentrationStatus.ELEVATED
    return PortfolioExposureConcentrationStatus.NORMAL


def _risk_pressure_state(concentration_status: str, portfolio_state: str) -> str:
    if portfolio_state == 'BLOCK_NEW_ENTRIES' or concentration_status == PortfolioExposureConcentrationStatus.CRITICAL:
        return PortfolioExposureRiskPressureState.BLOCK_NEW_EXPOSURE
    if portfolio_state == 'THROTTLED' or concentration_status == PortfolioExposureConcentrationStatus.HIGH:
        return PortfolioExposureRiskPressureState.THROTTLED
    if concentration_status == PortfolioExposureConcentrationStatus.ELEVATED or portfolio_state == 'CAUTION':
        return PortfolioExposureRiskPressureState.CAUTION
    return PortfolioExposureRiskPressureState.NORMAL


def _build_cluster_key(*, market_slug: str, market_category: str, direction: str) -> tuple[str, str]:
    return market_slug or 'unknown-market', f'{market_category or "uncategorized"}:{direction}'


def build_cluster_snapshots(*, run: PortfolioExposureCoordinationRun, portfolio_throttle_state: str = 'NORMAL') -> list[PortfolioExposureClusterSnapshot]:
    clusters: dict[tuple[str, str], dict] = defaultdict(lambda: {
        'market_slug': '',
        'market_category': '',
        'direction_counts': defaultdict(int),
        'session_ids': set(),
        'position_count': 0,
        'pending_dispatch_count': 0,
        'aggregate_notional_pressure': Decimal('0'),
        'admission_by_session': {},
        'dispatch_by_session': {},
    })

    positions = PaperPosition.objects.filter(status=PaperPositionStatus.OPEN, quantity__gt=0).select_related('market')
    for position in positions:
        direction = _direction_from_side(position.side)
        key = _build_cluster_key(
            market_slug=getattr(position.market, 'slug', '') or '',
            market_category=getattr(position.market, 'category', '') or '',
            direction=direction,
        )
        cluster = clusters[key]
        cluster['market_slug'] = getattr(position.market, 'slug', '') or ''
        cluster['market_category'] = getattr(position.market, 'category', '') or ''
        cluster['direction_counts'][direction] += 1
        cluster['position_count'] += 1
        cluster['aggregate_notional_pressure'] += position.market_value or Decimal('0')

    dispatches = AutonomousDispatchRecord.objects.filter(dispatch_status__in=PENDING_DISPATCH_STATUSES).select_related(
        'linked_execution_decision__linked_intake_candidate__linked_market',
        'linked_trade_execution__linked_candidate',
    )
    for dispatch in dispatches:
        intake_candidate = getattr(dispatch.linked_execution_decision, 'linked_intake_candidate', None)
        market = getattr(intake_candidate, 'linked_market', None)
        direction = 'NEUTRAL'
        execution_candidate = getattr(dispatch.linked_trade_execution, 'linked_candidate', None)
        if execution_candidate is not None:
            metadata = execution_candidate.metadata or {}
            direction = str(metadata.get('direction', direction)).upper()
            if direction not in {'LONG', 'SHORT'}:
                direction = 'NEUTRAL'
        key = _build_cluster_key(
            market_slug=getattr(market, 'slug', '') or 'dispatch-unmapped',
            market_category=getattr(market, 'category', '') or '',
            direction=direction,
        )
        cluster = clusters[key]
        cluster['market_slug'] = getattr(market, 'slug', '') or cluster['market_slug']
        cluster['market_category'] = getattr(market, 'category', '') or cluster['market_category']
        cluster['direction_counts'][direction] += 1
        cluster['pending_dispatch_count'] += 1
        cluster['aggregate_notional_pressure'] += dispatch.dispatched_notional or Decimal('0')
        session_id = (dispatch.metadata or {}).get('linked_session_id')
        if session_id:
            cluster['session_ids'].add(int(session_id))
            cluster['dispatch_by_session'][int(session_id)] = dispatch

    active_sessions = AutonomousRuntimeSession.objects.filter(session_status__in=ACTIVE_SESSION_STATUSES)
    latest_admission_by_session: dict[int, AutonomousSessionAdmissionDecision] = {}
    for admission in AutonomousSessionAdmissionDecision.objects.filter(linked_session__in=active_sessions).order_by('linked_session_id', '-created_at'):
        if admission.linked_session_id not in latest_admission_by_session:
            latest_admission_by_session[admission.linked_session_id] = admission

    market_map = {m.slug: m for m in Market.objects.filter(slug__in={x[0] for x in clusters.keys() if x[0]})}
    snapshots: list[PortfolioExposureClusterSnapshot] = []
    for (market_slug, mixed_key), cluster_data in clusters.items():
        for session in active_sessions:
            metadata = session.metadata or {}
            session_market = str(metadata.get('market_slug', '')).strip()
            if session_market and session_market == market_slug:
                cluster_data['session_ids'].add(session.id)
                admission = latest_admission_by_session.get(session.id)
                if admission is not None:
                    cluster_data['admission_by_session'][session.id] = admission

        net_direction = _aggregate_net_direction(cluster_data['direction_counts'])
        concentration_status = _concentration_status(
            session_count=len(cluster_data['session_ids']),
            pending_dispatch_count=cluster_data['pending_dispatch_count'],
            open_position_count=cluster_data['position_count'],
        )
        pressure_state = _risk_pressure_state(concentration_status, portfolio_throttle_state)

        linked_market = market_map.get(market_slug)
        cluster_type = PortfolioExposureClusterType.MARKET if linked_market else PortfolioExposureClusterType.MIXED
        snapshot = PortfolioExposureClusterSnapshot.objects.create(
            linked_run=run,
            cluster_label=f'{market_slug}::{mixed_key}',
            cluster_type=cluster_type,
            linked_market=linked_market,
            net_direction=net_direction,
            session_count=len(cluster_data['session_ids']),
            open_position_count=cluster_data['position_count'],
            pending_dispatch_count=cluster_data['pending_dispatch_count'],
            aggregate_notional_pressure=cluster_data['aggregate_notional_pressure'],
            aggregate_risk_pressure_state=pressure_state,
            concentration_status=concentration_status,
            cluster_summary='Cluster built from active paper positions, pending dispatches, and admitted runtime sessions.',
            reason_codes=['clustered_by_market_direction', f'portfolio_state_{portfolio_throttle_state.lower()}'],
            metadata={
                'market_slug': market_slug,
                'market_category': cluster_data['market_category'],
                'direction_counts': dict(cluster_data['direction_counts']),
                'paper_only': True,
            },
        )
        snapshots.append(snapshot)

        for session_id in sorted(cluster_data['session_ids']):
            session = active_sessions.filter(id=session_id).first()
            if session is None:
                continue
            admission = cluster_data['admission_by_session'].get(session_id)
            dispatch = cluster_data['dispatch_by_session'].get(session_id)
            direction_counts = cluster_data['direction_counts']
            long_count = direction_counts.get('LONG', 0)
            short_count = direction_counts.get('SHORT', 0)
            is_conflicting = long_count > 0 and short_count > 0
            role = SessionExposureContributionRole.SUPPORTING
            if is_conflicting:
                role = SessionExposureContributionRole.CONFLICTING
            elif cluster_data['pending_dispatch_count'] >= 2 and not dispatch:
                role = SessionExposureContributionRole.REDUNDANT
            elif session.session_status == 'PAUSED':
                role = SessionExposureContributionRole.LOW_VALUE
            elif dispatch is not None:
                role = SessionExposureContributionRole.PRIMARY_DRIVER

            if cluster_data['aggregate_notional_pressure'] >= Decimal('8000'):
                strength = SessionExposureContributionStrength.HIGH
            elif cluster_data['aggregate_notional_pressure'] >= Decimal('2000'):
                strength = SessionExposureContributionStrength.MEDIUM
            else:
                strength = SessionExposureContributionStrength.LOW

            SessionExposureContribution.objects.create(
                linked_session=session,
                linked_cluster_snapshot=snapshot,
                linked_admission_decision=admission,
                linked_dispatch_record=dispatch,
                linked_trade_execution=dispatch.linked_trade_execution if dispatch else None,
                contribution_role=role,
                contribution_direction=SessionExposureContributionDirection.MIXED if is_conflicting else (
                    SessionExposureContributionDirection.LONG if net_direction == PortfolioExposureNetDirection.LONG_BIAS else (
                        SessionExposureContributionDirection.SHORT if net_direction == PortfolioExposureNetDirection.SHORT_BIAS else SessionExposureContributionDirection.NEUTRAL
                    )
                ),
                contribution_strength=strength,
                contribution_summary='Session contribution inferred from cluster directionality, dispatch pressure, and runtime status.',
                reason_codes=[role.lower(), f'session_status_{session.session_status.lower()}'],
                metadata={'profile_slug': session.profile_slug, 'runtime_mode': session.runtime_mode, 'paper_only': True},
            )

    return snapshots

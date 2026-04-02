from __future__ import annotations

from django.utils import timezone

from apps.operator_queue.models import OperatorQueueItem
from apps.position_manager.models import PositionLifecycleDecision
from apps.runtime_governor.services import get_runtime_state
from apps.safety_guard.services import get_safety_status

from apps.portfolio_governor.models import (
    PortfolioExposureCoordinationRun,
    PortfolioExposureSnapshot,
    PortfolioGovernanceRun,
    PortfolioGovernanceRunStatus,
    PortfolioThrottleDecision,
)
from apps.portfolio_governor.services.exposure import build_exposure_snapshot_payload
from apps.portfolio_governor.services.profiles import get_profile, list_profiles
from apps.portfolio_governor.services.regime import detect_regime_signals
from apps.portfolio_governor.services.throttle import build_throttle_decision_payload


def run_portfolio_governance(*, profile_slug: str | None = None, triggered_by: str = 'manual_api') -> PortfolioGovernanceRun:
    profile = get_profile(profile_slug)
    run = PortfolioGovernanceRun.objects.create(
        status=PortfolioGovernanceRunStatus.RUNNING,
        profile_slug=profile['slug'],
        started_at=timezone.now(),
        details={'triggered_by': triggered_by, 'paper_demo_only': True, 'real_execution_enabled': False},
    )

    snapshot_payload = build_exposure_snapshot_payload()
    snapshot = PortfolioExposureSnapshot.objects.create(**snapshot_payload)

    queue_pressure = OperatorQueueItem.objects.filter(status__in=['PENDING', 'IN_PROGRESS']).count()
    close_reduce_events = PositionLifecycleDecision.objects.filter(status__in=['REDUCE', 'CLOSE']).order_by('-created_at', '-id')[:10].count()
    runtime = get_runtime_state()
    safety = get_safety_status()

    regime_signals = detect_regime_signals(
        snapshot=snapshot_payload,
        profile=profile,
        queue_pressure=queue_pressure,
        close_reduce_events=close_reduce_events,
    )
    decision_payload = build_throttle_decision_payload(
        snapshot=snapshot_payload,
        profile=profile,
        regime_signals=regime_signals,
        queue_pressure=queue_pressure,
        close_reduce_events=close_reduce_events,
        runtime_mode=runtime.current_mode,
        safety_status=safety,
    )
    decision = PortfolioThrottleDecision.objects.create(**decision_payload)

    run.exposure_snapshot = snapshot
    run.throttle_decision = decision
    run.status = PortfolioGovernanceRunStatus.COMPLETED
    run.finished_at = timezone.now()
    run.summary = f"Portfolio governance {decision.state}: positions={snapshot.open_positions}, exposure={snapshot.total_exposure}, drawdown={snapshot.recent_drawdown_pct}."
    run.details = {
        **run.details,
        'runtime_mode': runtime.current_mode,
        'safety_status': safety.get('status'),
        'regime_signals': regime_signals,
    }
    run.save(update_fields=['exposure_snapshot', 'throttle_decision', 'status', 'finished_at', 'summary', 'details', 'updated_at'])
    return run


def get_latest_exposure_snapshot() -> PortfolioExposureSnapshot | None:
    return PortfolioExposureSnapshot.objects.order_by('-created_at_snapshot', '-id').first()


def get_latest_throttle_decision() -> PortfolioThrottleDecision | None:
    return PortfolioThrottleDecision.objects.order_by('-created_at_decision', '-id').first()


def build_governance_summary() -> dict:
    latest_run = PortfolioGovernanceRun.objects.order_by('-started_at', '-id').first()
    latest_snapshot = get_latest_exposure_snapshot()
    latest_decision = get_latest_throttle_decision()
    latest_exposure_coordination = PortfolioExposureCoordinationRun.objects.order_by('-started_at', '-id').first()
    return {
        'latest_run': latest_run.id if latest_run else None,
        'latest_throttle_state': latest_decision.state if latest_decision else 'NORMAL',
        'open_positions': latest_snapshot.open_positions if latest_snapshot else 0,
        'total_exposure': str(latest_snapshot.total_exposure) if latest_snapshot else '0',
        'market_concentration': str(latest_snapshot.concentration_market_ratio) if latest_snapshot else '0',
        'provider_concentration': str(latest_snapshot.concentration_provider_ratio) if latest_snapshot else '0',
        'drawdown_signal': str(latest_snapshot.recent_drawdown_pct) if latest_snapshot else '0',
        'latest_exposure_coordination_run': latest_exposure_coordination.id if latest_exposure_coordination else None,
        'exposure_coordination_clusters_reviewed': latest_exposure_coordination.considered_cluster_count if latest_exposure_coordination else 0,
        'exposure_coordination_manual_reviews': latest_exposure_coordination.manual_review_count if latest_exposure_coordination else 0,
        'profiles': list_profiles(),
        'paper_demo_only': True,
        'real_execution_enabled': False,
    }

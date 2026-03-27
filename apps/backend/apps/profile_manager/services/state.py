from __future__ import annotations

from apps.operator_queue.models import OperatorQueueItem
from apps.portfolio_governor.services import get_latest_exposure_snapshot, get_latest_throttle_decision
from apps.position_manager.models import PositionLifecycleDecision
from apps.readiness_lab.models import ReadinessAssessmentRun
from apps.runtime_governor.services import get_runtime_state
from apps.safety_guard.services import get_safety_status


def build_profile_state_snapshot() -> dict:
    runtime = get_runtime_state()
    safety = get_safety_status()
    readiness = ReadinessAssessmentRun.objects.select_related('readiness_profile').order_by('-created_at', '-id').first()
    throttle = get_latest_throttle_decision()
    exposure = get_latest_exposure_snapshot()

    queue_pressure = OperatorQueueItem.objects.filter(status__in=['PENDING', 'IN_PROGRESS']).count()
    recent_defensive_actions = PositionLifecycleDecision.objects.filter(status__in=['REDUCE', 'CLOSE']).order_by('-created_at', '-id')[:12].count()

    return {
        'runtime_mode': runtime.current_mode,
        'runtime_status': runtime.status,
        'safety_status': safety.get('status', 'UNKNOWN'),
        'safety_kill_switch': bool(safety.get('kill_switch_enabled')),
        'safety_hard_stop': bool(safety.get('hard_stop_active')),
        'readiness_status': readiness.status if readiness else 'UNKNOWN',
        'queue_pressure': queue_pressure,
        'recent_defensive_actions': recent_defensive_actions,
        'throttle_state': throttle.state if throttle else 'NORMAL',
        'drawdown_pct': float(exposure.recent_drawdown_pct) if exposure else 0.0,
        'market_concentration': float(exposure.concentration_market_ratio) if exposure else 0.0,
        'provider_concentration': float(exposure.concentration_provider_ratio) if exposure else 0.0,
        'open_positions': exposure.open_positions if exposure else 0,
    }

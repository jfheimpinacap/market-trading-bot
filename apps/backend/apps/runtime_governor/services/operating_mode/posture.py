from __future__ import annotations

from collections import Counter

from apps.incident_commander.models import IncidentRecord, IncidentSeverity, IncidentStatus
from apps.mission_control.governance_backlog_pressure.services.run import governance_backlog_pressure_summary
from apps.mission_control.models import (
    AutonomousSessionAdmissionDecision,
    AutonomousSessionAdmissionDecisionType,
    AutonomousSessionHealthSnapshot,
    AutonomousSessionHealthStatus,
    AutonomousSessionRecoverySnapshot,
    AutonomousTimingDecision,
    AutonomousTimingDecisionType,
)
from apps.portfolio_governor.models import (
    PortfolioExposureApplyRecord,
    PortfolioExposureApplyRecordStatus,
    PortfolioExposureDecision,
    PortfolioExposureDecisionType,
)
from apps.runtime_governor.models import (
    AdmissionPressureState,
    ExposurePressureState,
    GlobalRuntimePostureRun,
    GlobalRuntimePostureSnapshot,
    IncidentPressureState,
    PortfolioPressureState,
    RecentLossState,
    RuntimePostureState,
    SafetyPostureState,
    SessionHealthState,
    SignalQualityState,
)
from apps.runtime_governor.services.state import get_runtime_state
from apps.safety_guard.services.evaluation import get_safety_status


def _derive_exposure_state() -> str:
    latest = PortfolioExposureDecision.objects.order_by('-created_at_decision', '-id').first()
    if not latest:
        return ExposurePressureState.NORMAL
    if latest.decision_type in {PortfolioExposureDecisionType.PAUSE_CLUSTER_ACTIVITY, PortfolioExposureDecisionType.REQUIRE_MANUAL_EXPOSURE_REVIEW}:
        return ExposurePressureState.BLOCK_NEW_ACTIVITY
    if latest.decision_type in {PortfolioExposureDecisionType.THROTTLE_NEW_ENTRIES, PortfolioExposureDecisionType.DEFER_PENDING_DISPATCH}:
        return ExposurePressureState.THROTTLED
    if latest.decision_type == PortfolioExposureDecisionType.PARK_WEAKER_SESSION:
        return ExposurePressureState.CAUTION
    return ExposurePressureState.NORMAL


def _derive_admission_state() -> str:
    latest = AutonomousSessionAdmissionDecision.objects.order_by('-created_at', '-id').first()
    if not latest:
        return AdmissionPressureState.NORMAL
    if latest.decision_type in {AutonomousSessionAdmissionDecisionType.REQUIRE_MANUAL_ADMISSION_REVIEW, AutonomousSessionAdmissionDecisionType.RETIRE_SESSION}:
        return AdmissionPressureState.BLOCKED
    if latest.decision_type in {AutonomousSessionAdmissionDecisionType.PAUSE_SESSION, AutonomousSessionAdmissionDecisionType.DEFER_SESSION}:
        return AdmissionPressureState.THROTTLED
    if latest.decision_type == AutonomousSessionAdmissionDecisionType.PARK_SESSION:
        return AdmissionPressureState.CAUTION
    return AdmissionPressureState.NORMAL


def _derive_session_health_state() -> str:
    latest = AutonomousSessionHealthSnapshot.objects.order_by('-created_at', '-id').first()
    if not latest:
        return SessionHealthState.HEALTHY
    mapping = {
        AutonomousSessionHealthStatus.HEALTHY: SessionHealthState.HEALTHY,
        AutonomousSessionHealthStatus.CAUTION: SessionHealthState.CAUTION,
        AutonomousSessionHealthStatus.DEGRADED: SessionHealthState.DEGRADED,
        AutonomousSessionHealthStatus.BLOCKED: SessionHealthState.BLOCKED,
        AutonomousSessionHealthStatus.STALLED: SessionHealthState.DEGRADED,
    }
    return mapping.get(latest.session_health_status, SessionHealthState.CAUTION)


def _derive_recent_loss_state() -> str:
    latest = AutonomousSessionHealthSnapshot.objects.order_by('-created_at', '-id').first()
    if not latest or latest.recent_loss_count <= 0:
        return RecentLossState.NONE
    return RecentLossState.REPEATED_LOSS if latest.recent_loss_count >= 2 else RecentLossState.RECENT_LOSS


def _derive_signal_quality_state() -> str:
    latest = AutonomousTimingDecision.objects.order_by('-created_at', '-id').first()
    if not latest:
        return SignalQualityState.NORMAL
    if latest.decision_type == AutonomousTimingDecisionType.RUN_NOW:
        return SignalQualityState.STRONG
    if latest.decision_type in {AutonomousTimingDecisionType.WAIT_SHORT, AutonomousTimingDecisionType.WAIT_LONG}:
        return SignalQualityState.NORMAL
    if latest.decision_type == AutonomousTimingDecisionType.MONITOR_ONLY_NEXT:
        return SignalQualityState.QUIET
    return SignalQualityState.WEAK


def _derive_runtime_and_safety_posture() -> tuple[str, str]:
    state = get_runtime_state()
    runtime_posture = RuntimePostureState.NORMAL
    if state.status in {'DEGRADED', 'PAUSED'}:
        runtime_posture = RuntimePostureState.CAUTION
    elif state.status == 'STOPPED':
        runtime_posture = RuntimePostureState.BLOCKED

    safety = get_safety_status()
    if safety.get('kill_switch_enabled') or safety.get('hard_stop_active'):
        safety_posture = SafetyPostureState.HARD_BLOCK
    elif safety.get('status') in {'COOLDOWN', 'PAUSED'}:
        safety_posture = SafetyPostureState.CAUTION
    else:
        safety_posture = SafetyPostureState.NORMAL
    return runtime_posture, safety_posture


def _derive_incident_pressure_state() -> str:
    active = IncidentRecord.objects.filter(status__in=[IncidentStatus.OPEN, IncidentStatus.MITIGATING, IncidentStatus.DEGRADED, IncidentStatus.ESCALATED])
    critical_count = active.filter(severity=IncidentSeverity.CRITICAL).count()
    high_count = active.filter(severity=IncidentSeverity.HIGH).count()
    if critical_count > 0:
        return IncidentPressureState.HIGH
    if high_count > 0 or active.count() >= 2:
        return IncidentPressureState.CAUTION
    return IncidentPressureState.NONE


def _derive_portfolio_pressure_state() -> str:
    latest_apply = PortfolioExposureApplyRecord.objects.order_by('-created_at_record', '-id').first()
    if latest_apply and latest_apply.record_status == PortfolioExposureApplyRecordStatus.BLOCKED:
        return PortfolioPressureState.BLOCK_NEW_ENTRIES
    exposure = _derive_exposure_state()
    if exposure == ExposurePressureState.BLOCK_NEW_ACTIVITY:
        return PortfolioPressureState.BLOCK_NEW_ENTRIES
    if exposure == ExposurePressureState.THROTTLED:
        return PortfolioPressureState.THROTTLED
    if exposure == ExposurePressureState.CAUTION:
        return PortfolioPressureState.CAUTION
    return PortfolioPressureState.NORMAL


def build_posture_snapshot(*, posture_run: GlobalRuntimePostureRun | None = None) -> GlobalRuntimePostureSnapshot:
    reason_codes: list[str] = []
    exposure_state = _derive_exposure_state()
    admission_state = _derive_admission_state()
    session_health_state = _derive_session_health_state()
    recent_loss_state = _derive_recent_loss_state()
    signal_quality_state = _derive_signal_quality_state()
    runtime_posture, safety_posture = _derive_runtime_and_safety_posture()
    incident_pressure = _derive_incident_pressure_state()
    portfolio_pressure = _derive_portfolio_pressure_state()
    governance_backlog_pressure_state = str(
        governance_backlog_pressure_summary().get('governance_backlog_pressure_state') or 'NORMAL'
    ).upper()
    if governance_backlog_pressure_state == 'HIGH' and runtime_posture == RuntimePostureState.NORMAL:
        runtime_posture = RuntimePostureState.CAUTION

    for label, value in {
        'exposure_pressure': exposure_state,
        'admission_pressure': admission_state,
        'session_health': session_health_state,
        'recent_loss': recent_loss_state,
        'signal_quality': signal_quality_state,
        'runtime_posture': runtime_posture,
        'safety_posture': safety_posture,
        'incident_pressure': incident_pressure,
        'portfolio_pressure': portfolio_pressure,
        'governance_backlog_pressure': governance_backlog_pressure_state,
    }.items():
        if value not in {'NORMAL', 'HEALTHY', 'NONE'}:
            reason_codes.append(f'{label}:{value}')

    summary = (
        f'Posture review found exposure={exposure_state}, admission={admission_state}, '
        f'health={session_health_state}, losses={recent_loss_state}, signal={signal_quality_state}, '
        f'runtime={runtime_posture}, safety={safety_posture}, incident={incident_pressure}, '
        f'portfolio={portfolio_pressure}, governance_backlog={governance_backlog_pressure_state}.'
    )

    metadata = {
        'signal_counter': dict(Counter(reason_codes)),
        'linked_models': {
            'timing_decisions': AutonomousTimingDecision.objects.count(),
            'health_snapshots': AutonomousSessionHealthSnapshot.objects.count(),
            'recovery_snapshots': AutonomousSessionRecoverySnapshot.objects.count(),
            'admission_decisions': AutonomousSessionAdmissionDecision.objects.count(),
            'exposure_decisions': PortfolioExposureDecision.objects.count(),
            'governance_backlog_pressure_state': governance_backlog_pressure_state,
        },
    }

    return GlobalRuntimePostureSnapshot.objects.create(
        linked_posture_run=posture_run,
        exposure_pressure_state=exposure_state,
        admission_pressure_state=admission_state,
        session_health_state=session_health_state,
        recent_loss_state=recent_loss_state,
        signal_quality_state=signal_quality_state,
        runtime_posture=runtime_posture,
        safety_posture=safety_posture,
        incident_pressure_state=incident_pressure,
        portfolio_pressure_state=portfolio_pressure,
        snapshot_summary=summary,
        reason_codes=reason_codes,
        metadata=metadata,
    )

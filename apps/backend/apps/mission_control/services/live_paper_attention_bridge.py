from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.mission_control.models import (
    AutonomousHeartbeatDecision,
    AutonomousHeartbeatDecisionStatus,
    AutonomousHeartbeatDecisionType,
    AutonomousHeartbeatRun,
    AutonomousRuntimeSessionStatus,
)
from apps.mission_control.services.live_paper_bootstrap import get_live_paper_bootstrap_status
from apps.mission_control.services.session_health import build_session_health_summary
from apps.mission_control.services.session_heartbeat import build_heartbeat_summary
from apps.mission_control.services.session_recovery import build_session_recovery_summary
from apps.operator_alerts.models import (
    OperatorAlert,
    OperatorAlertSeverity,
    OperatorAlertSource,
    OperatorAlertStatus,
    OperatorAlertType,
)
from apps.operator_alerts.services.alerts import AlertEmitPayload, emit_alert, resolve_alert

LIVE_PAPER_ATTENTION_ALERT_DEDUPE_KEY = 'live_paper_autopilot_attention_global'

ATTENTION_MODE_HEALTHY = 'HEALTHY'
ATTENTION_MODE_DEGRADED = 'DEGRADED'
ATTENTION_MODE_REVIEW_NOW = 'REVIEW_NOW'
ATTENTION_MODE_BLOCKED = 'BLOCKED'

ALERT_ACTION_CREATED = 'CREATED'
ALERT_ACTION_UPDATED = 'UPDATED'
ALERT_ACTION_RESOLVED = 'RESOLVED'
ALERT_ACTION_NOOP = 'NOOP'

SUPPRESSION_REASON_NO_MATERIAL_CHANGE = 'NO_MATERIAL_CHANGE'
SUPPRESSION_REASON_ALERT_NOT_NEEDED = 'ALERT_NOT_NEEDED'
SUPPRESSION_REASON_NO_ACTIVE_ALERT = 'NO_ACTIVE_ALERT'

MATERIAL_CHANGE_FIELDS = (
    'attention_mode',
    'attention_needed',
    'alert_severity',
    'current_session_status',
    'attention_reason_codes',
)


def _active_bridge_alerts():
    return OperatorAlert.objects.filter(dedupe_key=LIVE_PAPER_ATTENTION_ALERT_DEDUPE_KEY).exclude(status=OperatorAlertStatus.RESOLVED)


def _active_signal_alert() -> OperatorAlert | None:
    return _active_bridge_alerts().exclude(status=OperatorAlertStatus.SUPPRESSED).order_by('-last_seen_at', '-id').first()


def _normalize_reason_codes(reason_codes: list[str]) -> list[str]:
    return sorted({str(code).strip().lower() for code in reason_codes if str(code).strip()})


def _resolve_attention_mode(*, status_payload: dict[str, Any], heartbeat_summary: dict[str, Any]) -> tuple[str, list[str]]:
    reason_codes: list[str] = []
    session_active = bool(status_payload.get('session_active'))
    heartbeat_active = bool(status_payload.get('heartbeat_active'))
    current_session_status = str(status_payload.get('current_session_status') or '').upper()
    operator_hint = str(status_payload.get('operator_attention_hint') or '').lower()

    latest_decision = AutonomousHeartbeatDecision.objects.order_by('-created_at', '-id').first()
    latest_decision_type = str(latest_decision.decision_type or '') if latest_decision else ''
    latest_decision_status = str(latest_decision.decision_status or '') if latest_decision else ''
    latest_run = AutonomousHeartbeatRun.objects.order_by('-started_at', '-id').first()
    latest_run_metadata = (latest_run.metadata or {}) if latest_run else {}

    health_summary = build_session_health_summary().get('summary', {})
    recovery_summary = build_session_recovery_summary().get('summary', {})
    runtime_tuning_sync = (heartbeat_summary.get('runtime_tuning_attention_sync') or {}) if isinstance(heartbeat_summary, dict) else {}

    if current_session_status == AutonomousRuntimeSessionStatus.BLOCKED:
        reason_codes.append('session_status_blocked')
    if latest_decision_type in {AutonomousHeartbeatDecisionType.BLOCK_SESSION, AutonomousHeartbeatDecisionType.STOP_SESSION}:
        reason_codes.append('heartbeat_decision_blocked')
    if 'blocked' in operator_hint or 'stop' in operator_hint:
        reason_codes.append('operator_hint_blocked')
    if reason_codes:
        return ATTENTION_MODE_BLOCKED, _normalize_reason_codes(reason_codes)

    if session_active and not heartbeat_active:
        reason_codes.append('session_active_heartbeat_inactive')
    if latest_decision_status == AutonomousHeartbeatDecisionStatus.BLOCKED:
        reason_codes.append('latest_heartbeat_blocked')
    if latest_decision_type in {AutonomousHeartbeatDecisionType.PAUSE_SESSION, AutonomousHeartbeatDecisionType.STOP_SESSION}:
        reason_codes.append('latest_heartbeat_needs_review')
    if (latest_run_metadata.get('runtime_tuning_attention_sync') or {}).get('human_attention_mode') == 'REVIEW_NOW':
        reason_codes.append('runtime_tuning_review_now')
    if reason_codes:
        return ATTENTION_MODE_REVIEW_NOW, _normalize_reason_codes(reason_codes)

    if current_session_status == AutonomousRuntimeSessionStatus.DEGRADED:
        reason_codes.append('session_status_degraded')
    if session_active and ((health_summary.get('manual_review_or_escalation', 0) or 0) > 0):
        reason_codes.append('session_health_manual_review')
    if session_active and ((recovery_summary.get('manual_review', 0) or 0) > 0 or (recovery_summary.get('incident_escalation', 0) or 0) > 0):
        reason_codes.append('session_recovery_attention')
    if runtime_tuning_sync.get('human_attention_mode') == 'REVIEW_SOON':
        reason_codes.append('runtime_tuning_review_soon')
    if reason_codes:
        return ATTENTION_MODE_DEGRADED, _normalize_reason_codes(reason_codes)

    return ATTENTION_MODE_HEALTHY, []


def _resolve_alert_severity(mode: str) -> str | None:
    if mode in {ATTENTION_MODE_BLOCKED, ATTENTION_MODE_REVIEW_NOW}:
        return OperatorAlertSeverity.HIGH
    if mode == ATTENTION_MODE_DEGRADED:
        return OperatorAlertSeverity.WARNING
    return None


def _build_material_signal(*, attention_mode: str, attention_needed: bool, alert_severity: str | None, current_session_status: str, attention_reason_codes: list[str]) -> dict[str, Any]:
    return {
        'attention_mode': attention_mode,
        'attention_needed': attention_needed,
        'alert_severity': alert_severity,
        'current_session_status': current_session_status,
        'attention_reason_codes': _normalize_reason_codes(attention_reason_codes),
    }


def _build_alert_summary(*, attention_mode: str, status_summary: str, attention_reason_codes: list[str]) -> str:
    reason_suffix = f" reason_codes={','.join(attention_reason_codes)}" if attention_reason_codes else ''
    return f'Live paper autopilot attention mode={attention_mode}.{reason_suffix} {status_summary}'.strip()


def _build_status_summary(*, attention_mode: str, attention_needed: bool, active_alert: OperatorAlert | None, session_active: bool, heartbeat_active: bool, current_session_status: str) -> str:
    if not attention_needed:
        if active_alert:
            return f'{attention_mode}: no attention required; sync should resolve stale alert'
        return (
            f'{attention_mode}: healthy/no attention '
            f'(session_active={session_active} heartbeat_active={heartbeat_active} status={current_session_status})'
        )
    if active_alert is None:
        return f'{attention_mode}: attention required but alert is not active yet'
    return f'{attention_mode}: active {active_alert.severity} operator alert'


def _detect_material_change(*, existing_alert: OperatorAlert | None, material_signal: dict[str, Any]) -> list[str]:
    if existing_alert is None:
        return list(MATERIAL_CHANGE_FIELDS)
    previous_signal = existing_alert.metadata or {}
    changed: list[str] = []
    for field in MATERIAL_CHANGE_FIELDS:
        if previous_signal.get(field) != material_signal.get(field):
            changed.append(field)
    return changed


@transaction.atomic
def sync_live_paper_attention_alert() -> dict[str, Any]:
    bootstrap_status = get_live_paper_bootstrap_status()
    heartbeat_summary = build_heartbeat_summary()

    session_active = bool(bootstrap_status.get('session_active'))
    heartbeat_active = bool(bootstrap_status.get('heartbeat_active'))
    current_session_status = str(bootstrap_status.get('current_session_status') or 'MISSING')
    status_summary = str(bootstrap_status.get('status_summary') or '')

    attention_mode, reason_codes = _resolve_attention_mode(status_payload=bootstrap_status, heartbeat_summary=heartbeat_summary)
    attention_needed = attention_mode != ATTENTION_MODE_HEALTHY
    alert_severity = _resolve_alert_severity(attention_mode)

    material_signal = _build_material_signal(
        attention_mode=attention_mode,
        attention_needed=attention_needed,
        alert_severity=alert_severity,
        current_session_status=current_session_status,
        attention_reason_codes=reason_codes,
    )

    existing_alert = _active_signal_alert()
    for alert in _active_bridge_alerts().exclude(id=existing_alert.id if existing_alert else None):
        resolve_alert(alert)

    alert_action = ALERT_ACTION_NOOP
    material_change_detected = False
    material_change_fields: list[str] = []
    update_suppressed = False
    suppression_reason: str | None = None
    active_alert = existing_alert

    if attention_needed and alert_severity:
        material_change_fields = _detect_material_change(existing_alert=existing_alert, material_signal=material_signal)
        material_change_detected = bool(material_change_fields)
        if existing_alert is None:
            active_alert = emit_alert(
                AlertEmitPayload(
                    alert_type=OperatorAlertType.RUNTIME,
                    severity=alert_severity,
                    title='Live paper autopilot operational attention',
                    summary=_build_alert_summary(
                        attention_mode=attention_mode,
                        status_summary=status_summary,
                        attention_reason_codes=reason_codes,
                    ),
                    source=OperatorAlertSource.RUNTIME,
                    dedupe_key=LIVE_PAPER_ATTENTION_ALERT_DEDUPE_KEY,
                    metadata={'bridge_type': 'live_paper_attention_bridge', **material_signal},
                )
            )
            alert_action = ALERT_ACTION_CREATED
        elif material_change_detected:
            active_alert = emit_alert(
                AlertEmitPayload(
                    alert_type=OperatorAlertType.RUNTIME,
                    severity=alert_severity,
                    title='Live paper autopilot operational attention',
                    summary=_build_alert_summary(
                        attention_mode=attention_mode,
                        status_summary=status_summary,
                        attention_reason_codes=reason_codes,
                    ),
                    source=OperatorAlertSource.RUNTIME,
                    dedupe_key=LIVE_PAPER_ATTENTION_ALERT_DEDUPE_KEY,
                    metadata={'bridge_type': 'live_paper_attention_bridge', **material_signal},
                )
            )
            alert_action = ALERT_ACTION_UPDATED
        else:
            alert_action = ALERT_ACTION_NOOP
            update_suppressed = True
            suppression_reason = SUPPRESSION_REASON_NO_MATERIAL_CHANGE
    else:
        resolved_any = False
        for alert in _active_bridge_alerts():
            resolve_alert(alert)
            resolved_any = True
        alert_action = ALERT_ACTION_RESOLVED if resolved_any else ALERT_ACTION_NOOP
        if not resolved_any:
            update_suppressed = True
            suppression_reason = SUPPRESSION_REASON_NO_ACTIVE_ALERT
        else:
            suppression_reason = SUPPRESSION_REASON_ALERT_NOT_NEEDED
        active_alert = None

    alert_status_summary = _build_status_summary(
        attention_mode=attention_mode,
        attention_needed=attention_needed,
        active_alert=active_alert,
        session_active=session_active,
        heartbeat_active=heartbeat_active,
        current_session_status=current_session_status,
    )

    return {
        'attention_needed': attention_needed,
        'attention_mode': attention_mode,
        'alert_action': alert_action,
        'alert_severity': alert_severity,
        'session_active': session_active,
        'heartbeat_active': heartbeat_active,
        'current_session_status': current_session_status,
        'attention_reason_codes': reason_codes,
        'status_summary': status_summary,
        'alert_status_summary': alert_status_summary,
        'material_change_detected': material_change_detected,
        'material_change_fields': material_change_fields,
        'update_suppressed': update_suppressed,
        'suppression_reason': suppression_reason,
        'active_alert_present': active_alert is not None,
    }


def get_live_paper_attention_alert_status() -> dict[str, Any]:
    bootstrap_status = get_live_paper_bootstrap_status()
    heartbeat_summary = build_heartbeat_summary()

    session_active = bool(bootstrap_status.get('session_active'))
    heartbeat_active = bool(bootstrap_status.get('heartbeat_active'))
    current_session_status = str(bootstrap_status.get('current_session_status') or 'MISSING')
    status_summary = str(bootstrap_status.get('status_summary') or '')
    attention_mode, _reason_codes = _resolve_attention_mode(status_payload=bootstrap_status, heartbeat_summary=heartbeat_summary)
    attention_needed = attention_mode != ATTENTION_MODE_HEALTHY

    active_alert = _active_signal_alert()
    latest_bridge_alert = OperatorAlert.objects.filter(dedupe_key=LIVE_PAPER_ATTENTION_ALERT_DEDUPE_KEY).order_by('-updated_at', '-id').first()
    last_sync_summary = latest_bridge_alert.summary if latest_bridge_alert else None
    last_alert_action = None
    if latest_bridge_alert and latest_bridge_alert.status == OperatorAlertStatus.RESOLVED:
        last_alert_action = ALERT_ACTION_RESOLVED
    elif active_alert:
        last_alert_action = ALERT_ACTION_UPDATED

    return {
        'attention_needed': attention_needed,
        'attention_mode': attention_mode,
        'active_alert_present': active_alert is not None,
        'active_alert_severity': active_alert.severity if active_alert else None,
        'session_active': session_active,
        'heartbeat_active': heartbeat_active,
        'current_session_status': current_session_status,
        'status_summary': status_summary,
        'last_alert_action': last_alert_action,
        'last_sync_summary': last_sync_summary,
    }

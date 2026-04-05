from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.operator_alerts.models import (
    OperatorAlert,
    OperatorAlertSeverity,
    OperatorAlertSource,
    OperatorAlertStatus,
    OperatorAlertType,
)
from apps.operator_alerts.services.alerts import AlertEmitPayload, emit_alert, resolve_alert
from apps.mission_control.models import AutonomousHeartbeatRun
from apps.runtime_governor.services.tuning_autotriage import (
    MODE_MONITOR_ONLY,
    MODE_NO_ACTION,
    MODE_REVIEW_NOW,
    MODE_REVIEW_SOON,
    build_tuning_autotriage_digest,
)
from apps.runtime_governor.services.tuning_autotriage_alert_stability import (
    build_existing_material_signal,
    build_material_signal,
    detect_material_change,
)

TUNING_AUTOTRIAGE_ALERT_DEDUPE_KEY = 'runtime_tuning_autotriage_global'

ALERT_ACTION_CREATED = 'CREATED'
ALERT_ACTION_UPDATED = 'UPDATED'
ALERT_ACTION_RESOLVED = 'RESOLVED'
ALERT_ACTION_NOOP = 'NOOP'

SUPPRESSION_REASON_NO_MATERIAL_CHANGE = 'NO_MATERIAL_CHANGE'
SUPPRESSION_REASON_ALERT_NOT_NEEDED = 'ALERT_NOT_NEEDED'
SUPPRESSION_REASON_NO_ACTIVE_ALERT = 'NO_ACTIVE_ALERT'


def _alert_needed(mode: str) -> bool:
    return mode in {MODE_REVIEW_NOW, MODE_REVIEW_SOON}


def _resolve_alert_severity(mode: str) -> str | None:
    if mode == MODE_REVIEW_NOW:
        return OperatorAlertSeverity.HIGH
    if mode == MODE_REVIEW_SOON:
        return OperatorAlertSeverity.WARNING
    return None


def _build_alert_summary(*, mode: str, next_recommended_scope: str | None, autotriage_summary: str) -> str:
    prefix = 'Runtime tuning attention required now' if mode == MODE_REVIEW_NOW else 'Runtime tuning review should be scheduled soon'
    if next_recommended_scope:
        return f'{prefix}. Next scope: {next_recommended_scope}. {autotriage_summary}'
    return f'{prefix}. {autotriage_summary}'


def _active_bridge_alerts():
    return OperatorAlert.objects.filter(dedupe_key=TUNING_AUTOTRIAGE_ALERT_DEDUPE_KEY).exclude(status=OperatorAlertStatus.RESOLVED)


def _active_signal_alert() -> OperatorAlert | None:
    return _active_bridge_alerts().exclude(status=OperatorAlertStatus.SUPPRESSED).order_by('-last_seen_at', '-id').first()


def _build_status_summary(*, mode: str, alert_needed: bool, active_alert: OperatorAlert | None, next_recommended_scope: str | None) -> str:
    if not alert_needed:
        if active_alert:
            return f'{mode}: bridge alert still active and should be synced to resolve'
        return f'{mode}: no active runtime tuning attention alert'

    if not active_alert:
        return f'{mode}: alert required but not active yet; run sync to create it'

    scope_suffix = f' (next: {next_recommended_scope})' if next_recommended_scope else ''
    return f'{mode}: active {active_alert.severity} attention alert{scope_suffix}'


@transaction.atomic
def sync_tuning_autotriage_attention_alert() -> dict[str, Any]:
    digest = build_tuning_autotriage_digest(top_n=3, include_monitor=False)
    mode = str(digest['human_attention_mode'])
    alert_needed = _alert_needed(mode)
    alert_severity = _resolve_alert_severity(mode)
    next_scope = digest.get('next_recommended_scope')
    autotriage_summary = str(digest.get('autotriage_summary', ''))
    material_signal = build_material_signal(
        digest=digest,
        mode=mode,
        alert_needed=alert_needed,
        alert_severity=alert_severity,
    )

    existing_alert = _active_signal_alert()
    alert_action = ALERT_ACTION_NOOP
    material_change_detected = False
    material_change_fields: list[str] = []
    update_suppressed = False
    suppression_reason: str | None = None

    if alert_needed and alert_severity:
        if existing_alert is None:
            alert = emit_alert(
                AlertEmitPayload(
                    alert_type=OperatorAlertType.RUNTIME,
                    severity=alert_severity,
                    title='Runtime tuning human attention',
                    summary=_build_alert_summary(mode=mode, next_recommended_scope=next_scope, autotriage_summary=autotriage_summary),
                    source=OperatorAlertSource.RUNTIME,
                    dedupe_key=TUNING_AUTOTRIAGE_ALERT_DEDUPE_KEY,
                    metadata={
                        'bridge_type': 'runtime_tuning_autotriage_alert_bridge',
                        **material_signal,
                    },
                )
            )
            alert_action = ALERT_ACTION_CREATED
            material_change_detected = True
            material_change_fields = list(material_signal.keys())
            active_alert = alert
        else:
            material_change_fields = detect_material_change(
                previous_signal=build_existing_material_signal(existing_alert),
                current_signal=material_signal,
            )
            material_change_detected = bool(material_change_fields)
            if material_change_detected:
                alert = emit_alert(
                    AlertEmitPayload(
                        alert_type=OperatorAlertType.RUNTIME,
                        severity=alert_severity,
                        title='Runtime tuning human attention',
                        summary=_build_alert_summary(mode=mode, next_recommended_scope=next_scope, autotriage_summary=autotriage_summary),
                        source=OperatorAlertSource.RUNTIME,
                        dedupe_key=TUNING_AUTOTRIAGE_ALERT_DEDUPE_KEY,
                        metadata={
                            'bridge_type': 'runtime_tuning_autotriage_alert_bridge',
                            **material_signal,
                        },
                    )
                )
                alert_action = ALERT_ACTION_UPDATED
                active_alert = alert
            else:
                alert_action = ALERT_ACTION_NOOP
                update_suppressed = True
                suppression_reason = SUPPRESSION_REASON_NO_MATERIAL_CHANGE
                active_alert = existing_alert
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

    return {
        'human_attention_mode': mode,
        'alert_needed': alert_needed,
        'alert_action': alert_action,
        'alert_severity': alert_severity,
        'next_recommended_scope': next_scope,
        'autotriage_summary': autotriage_summary,
        'material_change_detected': material_change_detected,
        'material_change_fields': material_change_fields,
        'update_suppressed': update_suppressed,
        'suppression_reason': suppression_reason,
        'active_alert_present': active_alert is not None,
        'alert_status_summary': _build_status_summary(
            mode=mode,
            alert_needed=alert_needed,
            active_alert=active_alert,
            next_recommended_scope=next_scope,
        ),
    }


def get_tuning_autotriage_attention_alert_status() -> dict[str, Any]:
    digest = build_tuning_autotriage_digest(top_n=3, include_monitor=False)
    mode = str(digest['human_attention_mode'])
    alert_needed = _alert_needed(mode)
    next_scope = digest.get('next_recommended_scope')
    autotriage_summary = str(digest.get('autotriage_summary', ''))

    active_alert = _active_signal_alert()
    latest_heartbeat_run = AutonomousHeartbeatRun.objects.order_by('-started_at', '-id').first()
    heartbeat_sync = ((latest_heartbeat_run.metadata or {}).get('runtime_tuning_attention_sync') if latest_heartbeat_run else None) or None
    last_sync_action = heartbeat_sync.get('alert_action') if isinstance(heartbeat_sync, dict) else None
    last_sync_summary = heartbeat_sync.get('sync_summary') if isinstance(heartbeat_sync, dict) else None
    last_material_change_detected = (
        heartbeat_sync.get('material_change_detected')
        if isinstance(heartbeat_sync, dict) and 'material_change_detected' in heartbeat_sync
        else None
    )
    return {
        'human_attention_mode': mode,
        'alert_needed': alert_needed,
        'active_alert_present': active_alert is not None,
        'active_alert_severity': active_alert.severity if active_alert else None,
        'next_recommended_scope': next_scope,
        'autotriage_summary': autotriage_summary,
        'status_summary': _build_status_summary(
            mode=mode,
            alert_needed=alert_needed,
            active_alert=active_alert,
            next_recommended_scope=next_scope,
        ),
        'last_alert_action': last_sync_action,
        'last_sync_summary': last_sync_summary,
        'material_change_detected': last_material_change_detected,
        'runtime_tuning_attention_sync': heartbeat_sync,
    }

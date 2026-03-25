from __future__ import annotations

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.continuous_demo.models import ContinuousDemoSession, SessionStatus
from apps.operator_alerts.models import OperatorAlertSeverity, OperatorAlertSource, OperatorAlertType
from apps.operator_alerts.services.alerts import AlertEmitPayload, emit_alert
from apps.operator_queue.models import OperatorQueueItem, OperatorQueuePriority, OperatorQueueStatus
from apps.readiness_lab.models import ReadinessAssessmentRun, ReadinessStatus
from apps.real_data_sync.models import ProviderSyncRun, ProviderSyncStatus
from apps.runtime_governor.models import RuntimeMode, RuntimeModeState, RuntimeStateStatus
from apps.safety_guard.models import SafetyEvent, SafetyEventType, SafetyPolicyConfig, SafetyStatus


def run_default_alert_aggregation() -> int:
    emitted = 0
    emitted += emit_queue_alerts()
    emitted += emit_safety_alerts()
    emitted += emit_runtime_alerts()
    emitted += emit_sync_alerts()
    emitted += emit_readiness_alerts()
    emitted += emit_continuous_demo_alerts()
    return emitted


def emit_queue_alerts() -> int:
    count = 0
    pending_high = OperatorQueueItem.objects.filter(status=OperatorQueueStatus.PENDING, priority__in=[OperatorQueuePriority.HIGH, OperatorQueuePriority.CRITICAL]).count()
    pending_total = OperatorQueueItem.objects.filter(status=OperatorQueueStatus.PENDING).count()

    if pending_high > 0:
        emit_alert(AlertEmitPayload(
            alert_type=OperatorAlertType.APPROVAL_REQUIRED,
            severity=OperatorAlertSeverity.HIGH if pending_high < 3 else OperatorAlertSeverity.CRITICAL,
            title='High-priority approvals are pending',
            summary=f'{pending_high} high/critical queue items need review.',
            source=OperatorAlertSource.OPERATOR_QUEUE,
            dedupe_key='queue:pending_high',
            metadata={'pending_high': pending_high, 'pending_total': pending_total},
        ))
        count += 1

    if pending_total >= 10:
        emit_alert(AlertEmitPayload(
            alert_type=OperatorAlertType.QUEUE,
            severity=OperatorAlertSeverity.WARNING,
            title='Operator queue backlog is elevated',
            summary=f'{pending_total} queue items are pending.',
            source=OperatorAlertSource.OPERATOR_QUEUE,
            dedupe_key='queue:pending_total',
            metadata={'pending_total': pending_total},
        ))
        count += 1

    stale_items = OperatorQueueItem.objects.filter(status=OperatorQueueStatus.PENDING, created_at__lt=timezone.now() - timedelta(hours=6), priority__in=[OperatorQueuePriority.HIGH, OperatorQueuePriority.CRITICAL]).count()
    if stale_items > 0:
        emit_alert(AlertEmitPayload(
            alert_type=OperatorAlertType.QUEUE,
            severity=OperatorAlertSeverity.HIGH,
            title='Critical queue items are stale',
            summary=f'{stale_items} high-priority queue items have been pending for over 6 hours.',
            source=OperatorAlertSource.OPERATOR_QUEUE,
            dedupe_key='queue:stale_critical',
            metadata={'stale_items': stale_items},
        ))
        count += 1
    return count


def emit_safety_alerts() -> int:
    count = 0
    config = SafetyPolicyConfig.objects.order_by('id').first()
    if not config:
        return count

    if config.kill_switch_enabled or config.status == SafetyStatus.KILL_SWITCH:
        emit_alert(AlertEmitPayload(
            alert_type=OperatorAlertType.SAFETY,
            severity=OperatorAlertSeverity.CRITICAL,
            title='Kill switch is active',
            summary='Autonomous execution is blocked until kill switch is disabled.',
            source=OperatorAlertSource.SAFETY,
            dedupe_key='safety:kill_switch',
            metadata={'status': config.status, 'kill_switch_enabled': config.kill_switch_enabled},
        ))
        count += 1

    if config.hard_stop_active or config.status == SafetyStatus.HARD_STOP:
        emit_alert(AlertEmitPayload(
            alert_type=OperatorAlertType.SAFETY,
            severity=OperatorAlertSeverity.CRITICAL,
            title='Hard stop is active',
            summary='Safety hard stop is active. Operator intervention required.',
            source=OperatorAlertSource.SAFETY,
            dedupe_key='safety:hard_stop',
            metadata={'status': config.status, 'hard_stop_active': config.hard_stop_active},
        ))
        count += 1

    if config.cooldown_until_cycle is not None:
        emit_alert(AlertEmitPayload(
            alert_type=OperatorAlertType.SAFETY,
            severity=OperatorAlertSeverity.WARNING,
            title='Safety cooldown is active',
            summary=f'Cooldown remains active until cycle {config.cooldown_until_cycle}.',
            source=OperatorAlertSource.SAFETY,
            dedupe_key='safety:cooldown',
            metadata={'cooldown_until_cycle': config.cooldown_until_cycle},
        ))
        count += 1

    day_ago = timezone.now() - timedelta(hours=24)
    pressure_count = SafetyEvent.objects.filter(created_at__gte=day_ago, event_type__in=[SafetyEventType.WARNING, SafetyEventType.ERROR_LIMIT_HIT, SafetyEventType.APPROVAL_ESCALATION]).count()
    if pressure_count >= 5:
        emit_alert(AlertEmitPayload(
            alert_type=OperatorAlertType.ANOMALY,
            severity=OperatorAlertSeverity.WARNING,
            title='Safety pressure is elevated',
            summary=f'{pressure_count} safety pressure events in the last 24h.',
            source=OperatorAlertSource.SAFETY,
            dedupe_key='safety:pressure',
            metadata={'pressure_count': pressure_count},
        ))
        count += 1
    return count


def emit_runtime_alerts() -> int:
    count = 0
    state = RuntimeModeState.objects.order_by('id').first()
    if not state:
        return count

    if state.status in [RuntimeStateStatus.DEGRADED, RuntimeStateStatus.STOPPED, RuntimeStateStatus.PAUSED]:
        emit_alert(AlertEmitPayload(
            alert_type=OperatorAlertType.RUNTIME,
            severity=OperatorAlertSeverity.HIGH if state.status != RuntimeStateStatus.STOPPED else OperatorAlertSeverity.CRITICAL,
            title='Runtime is degraded',
            summary=f'Runtime status is {state.status} in mode {state.current_mode}.',
            source=OperatorAlertSource.RUNTIME,
            dedupe_key='runtime:degraded',
            metadata={'status': state.status, 'mode': state.current_mode, 'set_by': state.set_by},
        ))
        count += 1

    if state.current_mode in [RuntimeMode.PAPER_ASSIST, RuntimeMode.OBSERVE_ONLY]:
        emit_alert(AlertEmitPayload(
            alert_type=OperatorAlertType.RUNTIME,
            severity=OperatorAlertSeverity.WARNING,
            title='Runtime is in conservative mode',
            summary=f'Current runtime mode is {state.current_mode}.',
            source=OperatorAlertSource.RUNTIME,
            dedupe_key='runtime:conservative_mode',
            metadata={'current_mode': state.current_mode},
        ))
        count += 1
    return count


def emit_sync_alerts() -> int:
    count = 0
    stale_cutoff = timezone.now() - timedelta(minutes=30)
    providers = ProviderSyncRun.objects.values_list('provider', flat=True).distinct()

    for provider in providers:
        latest = ProviderSyncRun.objects.filter(provider=provider).order_by('-started_at', '-id').first()
        if not latest:
            continue
        if latest.started_at < stale_cutoff:
            emit_alert(AlertEmitPayload(
                alert_type=OperatorAlertType.SYNC,
                severity=OperatorAlertSeverity.HIGH,
                title=f'{provider} sync is stale',
                summary=f'Latest sync started at {latest.started_at.isoformat()}.',
                source=OperatorAlertSource.REAL_SYNC,
                dedupe_key=f'sync:stale:{provider}',
                metadata={'provider': provider, 'latest_started_at': latest.started_at.isoformat()},
            ))
            count += 1

        if latest.status in [ProviderSyncStatus.FAILED, ProviderSyncStatus.PARTIAL]:
            emit_alert(AlertEmitPayload(
                alert_type=OperatorAlertType.SYNC,
                severity=OperatorAlertSeverity.WARNING,
                title=f'{provider} sync degraded',
                summary=f'Latest sync status is {latest.status}.',
                source=OperatorAlertSource.REAL_SYNC,
                dedupe_key=f'sync:degraded:{provider}',
                metadata={'provider': provider, 'status': latest.status, 'errors_count': latest.errors_count},
            ))
            count += 1

        recent_runs = ProviderSyncRun.objects.filter(provider=provider).order_by('-started_at', '-id')[:3]
        if recent_runs and all(run.status == ProviderSyncStatus.FAILED for run in recent_runs):
            emit_alert(AlertEmitPayload(
                alert_type=OperatorAlertType.SYNC,
                severity=OperatorAlertSeverity.CRITICAL,
                title=f'{provider} sync failing repeatedly',
                summary='The last 3 sync runs failed.',
                source=OperatorAlertSource.REAL_SYNC,
                dedupe_key=f'sync:failed_streak:{provider}',
                metadata={'provider': provider, 'failed_streak': 3},
            ))
            count += 1
    return count


def emit_readiness_alerts() -> int:
    assessment = ReadinessAssessmentRun.objects.order_by('-created_at', '-id').first()
    if not assessment:
        return 0

    previous = ReadinessAssessmentRun.objects.exclude(id=assessment.id).order_by('-created_at', '-id').first()
    count = 0
    if assessment.status == ReadinessStatus.NOT_READY:
        emit_alert(AlertEmitPayload(
            alert_type=OperatorAlertType.READINESS,
            severity=OperatorAlertSeverity.HIGH,
            title='Readiness status is NOT_READY',
            summary=assessment.summary or 'Readiness gates indicate the system is not ready to promote autonomy.',
            source=OperatorAlertSource.READINESS,
            dedupe_key='readiness:not_ready',
            metadata={'assessment_id': assessment.id, 'status': assessment.status},
        ))
        count += 1

    if previous and previous.status == ReadinessStatus.READY and assessment.status != ReadinessStatus.READY:
        emit_alert(AlertEmitPayload(
            alert_type=OperatorAlertType.READINESS,
            severity=OperatorAlertSeverity.WARNING,
            title='Readiness degraded from READY',
            summary=f'Readiness moved from {previous.status} to {assessment.status}.',
            source=OperatorAlertSource.READINESS,
            dedupe_key='readiness:degraded',
            metadata={'from': previous.status, 'to': assessment.status, 'assessment_id': assessment.id},
        ))
        count += 1
    return count


def emit_continuous_demo_alerts() -> int:
    count = 0
    latest_session = ContinuousDemoSession.objects.order_by('-started_at', '-id').first()
    if not latest_session:
        return count

    if latest_session.session_status in [SessionStatus.FAILED, SessionStatus.STOPPED] and latest_session.finished_at:
        emit_alert(AlertEmitPayload(
            alert_type=OperatorAlertType.RUNTIME,
            severity=OperatorAlertSeverity.HIGH if latest_session.session_status == SessionStatus.STOPPED else OperatorAlertSeverity.CRITICAL,
            title='Continuous demo session stopped unexpectedly',
            summary=latest_session.summary or f'Session ended with status {latest_session.session_status}.',
            source=OperatorAlertSource.CONTINUOUS_DEMO,
            dedupe_key='continuous_demo:session_stopped',
            metadata={'session_id': latest_session.id, 'status': latest_session.session_status},
        ))
        count += 1

    if latest_session.total_errors >= 3:
        emit_alert(AlertEmitPayload(
            alert_type=OperatorAlertType.ANOMALY,
            severity=OperatorAlertSeverity.WARNING,
            title='Continuous demo loop error rate elevated',
            summary=f'Session has {latest_session.total_errors} errors.',
            source=OperatorAlertSource.CONTINUOUS_DEMO,
            dedupe_key='continuous_demo:error_streak',
            metadata={'session_id': latest_session.id, 'total_errors': latest_session.total_errors},
        ))
        count += 1
    return count

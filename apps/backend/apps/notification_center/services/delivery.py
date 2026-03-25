import json
from urllib import request as urllib_request

from django.core.mail import send_mail
from django.utils import timezone

from apps.notification_center.models import (
    NotificationChannel,
    NotificationChannelType,
    NotificationDelivery,
    NotificationDeliveryMode,
    NotificationDeliveryStatus,
)
from apps.notification_center.services.routing import dedupe_or_cooldown_reason, evaluate_alert_rules, evaluate_digest_rules
from apps.operator_alerts.models import OperatorAlert, OperatorDigest


def _build_alert_payload(alert: OperatorAlert) -> dict:
    return {
        'kind': 'alert',
        'id': alert.id,
        'alert_type': alert.alert_type,
        'severity': alert.severity,
        'status': alert.status,
        'title': alert.title,
        'summary': alert.summary,
        'source': alert.source,
        'dedupe_key': alert.dedupe_key,
        'last_seen_at': alert.last_seen_at.isoformat(),
    }


def _build_digest_payload(digest: OperatorDigest) -> dict:
    return {
        'kind': 'digest',
        'id': digest.id,
        'digest_type': digest.digest_type,
        'window_start': digest.window_start.isoformat(),
        'window_end': digest.window_end.isoformat(),
        'summary': digest.summary,
        'alerts_count': digest.alerts_count,
        'critical_count': digest.critical_count,
    }


def _dispatch(channel: NotificationChannel, payload: dict) -> tuple[str, str, dict]:
    if channel.channel_type == NotificationChannelType.UI_ONLY:
        return NotificationDeliveryStatus.SENT, 'sent:ui_only', {'channel': 'ui_only'}

    if channel.channel_type == NotificationChannelType.WEBHOOK:
        endpoint = channel.config.get('url') if isinstance(channel.config, dict) else None
        if not endpoint:
            return NotificationDeliveryStatus.FAILED, 'failed:webhook_missing_url', {'error': 'missing webhook url'}
        headers = {'Content-Type': 'application/json'}
        for key, value in (channel.config.get('headers') or {}).items():
            headers[str(key)] = str(value)
        req = urllib_request.Request(endpoint, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib_request.urlopen(req, timeout=5) as response:
            code = getattr(response, 'status', None) or response.getcode()
            body = response.read(200).decode('utf-8', errors='ignore')
        if 200 <= int(code) < 300:
            return NotificationDeliveryStatus.SENT, 'sent:webhook', {'status_code': int(code), 'body_preview': body}
        return NotificationDeliveryStatus.FAILED, 'failed:webhook_status', {'status_code': int(code), 'body_preview': body}

    if channel.channel_type == NotificationChannelType.EMAIL:
        recipients = channel.config.get('recipients') if isinstance(channel.config, dict) else None
        if not recipients:
            return NotificationDeliveryStatus.FAILED, 'failed:email_missing_recipients', {'error': 'missing recipients'}
        subject = f"[market-trading-bot] {payload.get('kind', 'notification')} #{payload.get('id', 'n/a')}"
        send_mail(subject, json.dumps(payload, indent=2), None, recipients, fail_silently=False)
        return NotificationDeliveryStatus.SENT, 'sent:email', {'recipient_count': len(recipients)}

    return NotificationDeliveryStatus.SKIPPED, 'skipped:unsupported_channel_type', {'channel_type': channel.channel_type}


def _record_delivery(*, alert: OperatorAlert | None, digest: OperatorDigest | None, channel: NotificationChannel, mode: str, status: str, reason: str, payload: dict, metadata: dict, rule=None, fingerprint: str = '') -> NotificationDelivery:
    delivery = NotificationDelivery.objects.create(
        related_alert=alert,
        related_digest=digest,
        channel=channel,
        rule=rule,
        delivery_status=status,
        delivery_mode=mode,
        reason=reason,
        payload_preview=payload,
        response_metadata=metadata,
        fingerprint=fingerprint,
        delivered_at=timezone.now() if status == NotificationDeliveryStatus.SENT else None,
    )
    return delivery


def send_alert_notifications(alert: OperatorAlert, *, force: bool = False) -> list[NotificationDelivery]:
    deliveries: list[NotificationDelivery] = []
    evaluations = evaluate_alert_rules(alert)

    if not evaluations:
        return deliveries

    for evaluation in evaluations:
        for channel in evaluation.channels:
            suppressed, reason, fingerprint = dedupe_or_cooldown_reason(
                rule=evaluation.rule,
                channel=channel,
                alert=alert,
                digest=None,
                mode=NotificationDeliveryMode.IMMEDIATE,
            )
            payload = _build_alert_payload(alert)
            if suppressed and not force:
                deliveries.append(_record_delivery(
                    alert=alert,
                    digest=None,
                    channel=channel,
                    mode=NotificationDeliveryMode.IMMEDIATE,
                    status=NotificationDeliveryStatus.SUPPRESSED,
                    reason=reason,
                    payload=payload,
                    metadata={},
                    rule=evaluation.rule,
                    fingerprint=fingerprint,
                ))
                continue

            try:
                status, dispatch_reason, metadata = _dispatch(channel, payload)
            except Exception as exc:  # noqa: BLE001
                status, dispatch_reason, metadata = NotificationDeliveryStatus.FAILED, 'failed:exception', {'error': str(exc)}

            deliveries.append(_record_delivery(
                alert=alert,
                digest=None,
                channel=channel,
                mode=NotificationDeliveryMode.IMMEDIATE,
                status=status,
                reason=dispatch_reason,
                payload=payload,
                metadata=metadata,
                rule=evaluation.rule,
                fingerprint=fingerprint,
            ))

    return deliveries


def send_digest_notifications(digest: OperatorDigest, *, force: bool = False) -> list[NotificationDelivery]:
    deliveries: list[NotificationDelivery] = []
    evaluations = evaluate_digest_rules(digest)
    for evaluation in evaluations:
        for channel in evaluation.channels:
            suppressed, reason, fingerprint = dedupe_or_cooldown_reason(
                rule=evaluation.rule,
                channel=channel,
                alert=None,
                digest=digest,
                mode=NotificationDeliveryMode.DIGEST,
            )
            payload = _build_digest_payload(digest)
            if suppressed and not force:
                deliveries.append(_record_delivery(
                    alert=None,
                    digest=digest,
                    channel=channel,
                    mode=NotificationDeliveryMode.DIGEST,
                    status=NotificationDeliveryStatus.SUPPRESSED,
                    reason=reason,
                    payload=payload,
                    metadata={},
                    rule=evaluation.rule,
                    fingerprint=fingerprint,
                ))
                continue

            try:
                status, dispatch_reason, metadata = _dispatch(channel, payload)
            except Exception as exc:  # noqa: BLE001
                status, dispatch_reason, metadata = NotificationDeliveryStatus.FAILED, 'failed:exception', {'error': str(exc)}

            deliveries.append(_record_delivery(
                alert=None,
                digest=digest,
                channel=channel,
                mode=NotificationDeliveryMode.DIGEST,
                status=status,
                reason=dispatch_reason,
                payload=payload,
                metadata=metadata,
                rule=evaluation.rule,
                fingerprint=fingerprint,
            ))

    return deliveries

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.notification_center.models import (
    NotificationChannel,
    NotificationDelivery,
    NotificationDeliveryMode,
    NotificationDeliveryStatus,
    NotificationRule,
)
from apps.notification_center.services.channels import ensure_default_ui_channel
from apps.operator_alerts.models import OperatorAlert, OperatorDigest

SEVERITY_RANK = {'info': 0, 'warning': 1, 'high': 2, 'critical': 3}


@dataclass
class RuleEvaluation:
    rule: NotificationRule
    channels: list[NotificationChannel]


def _severity_meets_threshold(alert: OperatorAlert, threshold: str) -> bool:
    return SEVERITY_RANK.get(alert.severity, 0) >= SEVERITY_RANK.get(threshold, 0)


def _match_criteria(criteria: dict, *, alert: OperatorAlert | None = None, digest: OperatorDigest | None = None) -> bool:
    if alert is not None:
        alert_types = criteria.get('alert_types') or criteria.get('alert_type')
        if alert_types:
            expected = set(alert_types if isinstance(alert_types, list) else [alert_types])
            if alert.alert_type not in expected:
                return False

        sources = criteria.get('sources') or criteria.get('source')
        if sources:
            expected = set(sources if isinstance(sources, list) else [sources])
            if alert.source not in expected:
                return False

        statuses = criteria.get('statuses')
        if statuses:
            expected = set(statuses if isinstance(statuses, list) else [statuses])
            if alert.status not in expected:
                return False

        persistence = criteria.get('min_persistence_seconds')
        if persistence:
            elapsed = (alert.last_seen_at - alert.first_seen_at).total_seconds()
            if elapsed < int(persistence):
                return False

    if digest is not None:
        digest_types = criteria.get('digest_types') or criteria.get('digest_type')
        if digest_types:
            expected = set(digest_types if isinstance(digest_types, list) else [digest_types])
            if digest.digest_type not in expected:
                return False

    return True


def _get_channels(rule: NotificationRule) -> list[NotificationChannel]:
    channels = list(rule.channels.filter(is_enabled=True).order_by('id'))
    if not channels:
        channels = [ensure_default_ui_channel()]
    return channels


def evaluate_alert_rules(alert: OperatorAlert, *, allowed_modes: tuple[str, ...] | None = None) -> list[RuleEvaluation]:
    evaluations: list[RuleEvaluation] = []
    modes = allowed_modes or (NotificationDeliveryMode.IMMEDIATE,)
    for rule in NotificationRule.objects.filter(is_enabled=True, delivery_mode__in=modes).order_by('id'):
        if not _severity_meets_threshold(alert, rule.severity_threshold):
            continue
        if not _match_criteria(rule.match_criteria or {}, alert=alert):
            continue
        evaluations.append(RuleEvaluation(rule=rule, channels=_get_channels(rule)))
    return evaluations


def evaluate_digest_rules(digest: OperatorDigest) -> list[RuleEvaluation]:
    evaluations: list[RuleEvaluation] = []
    for rule in NotificationRule.objects.filter(is_enabled=True, delivery_mode=NotificationDeliveryMode.DIGEST).order_by('id'):
        if not _match_criteria(rule.match_criteria or {}, digest=digest):
            continue
        evaluations.append(RuleEvaluation(rule=rule, channels=_get_channels(rule)))
    return evaluations


def fingerprint_for(*, alert: OperatorAlert | None, digest: OperatorDigest | None, channel: NotificationChannel, mode: str) -> str:
    if alert is not None:
        key = alert.dedupe_key or f'alert:{alert.id}'
        return f'{mode}:{channel.slug}:{key}'
    return f'{mode}:{channel.slug}:digest:{digest.id if digest else "none"}'


def dedupe_or_cooldown_reason(*, rule: NotificationRule, channel: NotificationChannel, alert: OperatorAlert | None, digest: OperatorDigest | None, mode: str) -> tuple[bool, str, str]:
    now = timezone.now()
    fingerprint = fingerprint_for(alert=alert, digest=digest, channel=channel, mode=mode)

    dedupe_since = now - timedelta(seconds=rule.dedupe_window_seconds)
    dedupe_hit = NotificationDelivery.objects.filter(
        fingerprint=fingerprint,
        created_at__gte=dedupe_since,
        delivery_status__in=[NotificationDeliveryStatus.PENDING, NotificationDeliveryStatus.SENT],
    ).exists()
    if dedupe_hit:
        return True, 'suppressed:dedupe_window', fingerprint

    if alert is not None:
        cooldown_since = now - timedelta(seconds=rule.cooldown_seconds)
        cooldown_hit = NotificationDelivery.objects.filter(
            related_alert=alert,
            channel=channel,
            rule=rule,
            delivered_at__isnull=False,
            delivered_at__gte=cooldown_since,
            delivery_status=NotificationDeliveryStatus.SENT,
        ).exists()
        if cooldown_hit:
            return True, 'suppressed:cooldown', fingerprint

    return False, 'dispatch', fingerprint

from django.db import models

from apps.common.models import TimeStampedModel
from apps.operator_alerts.models import OperatorAlert, OperatorDigest


class NotificationChannelType(models.TextChoices):
    UI_ONLY = 'ui_only', 'UI only'
    EMAIL = 'email', 'Email'
    WEBHOOK = 'webhook', 'Webhook'
    TELEGRAM = 'telegram', 'Telegram'
    DISCORD = 'discord', 'Discord'
    SLACK = 'slack', 'Slack'


class NotificationDeliveryMode(models.TextChoices):
    IMMEDIATE = 'immediate', 'Immediate'
    DIGEST = 'digest', 'Digest'
    ESCALATION = 'escalation', 'Escalation'
    ESCALATION_ONLY = 'escalation_only', 'Escalation only'


class NotificationDeliveryStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    SENT = 'SENT', 'Sent'
    FAILED = 'FAILED', 'Failed'
    SKIPPED = 'SKIPPED', 'Skipped'
    SUPPRESSED = 'SUPPRESSED', 'Suppressed'


class NotificationChannel(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=64, unique=True)
    channel_type = models.CharField(max_length=20, choices=NotificationChannelType.choices)
    is_enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['name', 'id']


class NotificationRule(TimeStampedModel):
    name = models.CharField(max_length=160)
    is_enabled = models.BooleanField(default=True)
    match_criteria = models.JSONField(default=dict, blank=True)
    delivery_mode = models.CharField(max_length=20, choices=NotificationDeliveryMode.choices, default=NotificationDeliveryMode.IMMEDIATE)
    channels = models.ManyToManyField(NotificationChannel, related_name='rules', blank=True)
    severity_threshold = models.CharField(max_length=12, default='warning')
    cooldown_seconds = models.PositiveIntegerField(default=900)
    dedupe_window_seconds = models.PositiveIntegerField(default=600)

    class Meta:
        ordering = ['name', 'id']


class NotificationDelivery(TimeStampedModel):
    related_alert = models.ForeignKey(OperatorAlert, on_delete=models.SET_NULL, null=True, blank=True, related_name='notification_deliveries')
    related_digest = models.ForeignKey(OperatorDigest, on_delete=models.SET_NULL, null=True, blank=True, related_name='notification_deliveries')
    channel = models.ForeignKey(NotificationChannel, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    rule = models.ForeignKey(NotificationRule, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    delivery_status = models.CharField(max_length=12, choices=NotificationDeliveryStatus.choices, default=NotificationDeliveryStatus.PENDING)
    delivery_mode = models.CharField(max_length=20, choices=NotificationDeliveryMode.choices, default=NotificationDeliveryMode.IMMEDIATE)
    reason = models.TextField(blank=True)
    payload_preview = models.JSONField(default=dict, blank=True)
    response_metadata = models.JSONField(default=dict, blank=True)
    fingerprint = models.CharField(max_length=255, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['delivery_status', '-created_at']),
            models.Index(fields=['fingerprint', '-created_at']),
            models.Index(fields=['related_alert', '-created_at']),
            models.Index(fields=['related_digest', '-created_at']),
        ]

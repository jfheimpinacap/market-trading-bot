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


class NotificationTriggerSource(models.TextChoices):
    MANUAL = 'manual', 'Manual'
    AUTOMATIC = 'automatic', 'Automatic'
    DIGEST_AUTOMATION = 'digest_automation', 'Digest automation'
    ESCALATION = 'escalation', 'Escalation'


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


class NotificationAutomationState(TimeStampedModel):
    is_enabled = models.BooleanField(default=False)
    automatic_dispatch_enabled = models.BooleanField(default=True)
    automatic_digest_enabled = models.BooleanField(default=True)
    escalation_enabled = models.BooleanField(default=True)
    suppress_info_alerts_by_default = models.BooleanField(default=True)
    digest_interval_minutes = models.PositiveIntegerField(default=60)
    escalation_after_minutes = models.PositiveIntegerField(default=30)
    max_auto_notifications_per_window = models.PositiveIntegerField(default=40)
    automation_window_minutes = models.PositiveIntegerField(default=60)
    last_automatic_dispatch_at = models.DateTimeField(null=True, blank=True)
    last_digest_cycle_at = models.DateTimeField(null=True, blank=True)
    last_escalation_cycle_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)


class NotificationDelivery(TimeStampedModel):
    related_alert = models.ForeignKey(OperatorAlert, on_delete=models.SET_NULL, null=True, blank=True, related_name='notification_deliveries')
    related_digest = models.ForeignKey(OperatorDigest, on_delete=models.SET_NULL, null=True, blank=True, related_name='notification_deliveries')
    channel = models.ForeignKey(NotificationChannel, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    rule = models.ForeignKey(NotificationRule, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    delivery_status = models.CharField(max_length=12, choices=NotificationDeliveryStatus.choices, default=NotificationDeliveryStatus.PENDING)
    delivery_mode = models.CharField(max_length=20, choices=NotificationDeliveryMode.choices, default=NotificationDeliveryMode.IMMEDIATE)
    trigger_source = models.CharField(max_length=20, choices=NotificationTriggerSource.choices, default=NotificationTriggerSource.MANUAL)
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
            models.Index(fields=['trigger_source', '-created_at']),
        ]


class NotificationEscalationEvent(TimeStampedModel):
    alert = models.ForeignKey(OperatorAlert, on_delete=models.CASCADE, related_name='notification_escalations')
    severity = models.CharField(max_length=12)
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=16, default='TRIGGERED')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['severity', '-created_at']),
        ]

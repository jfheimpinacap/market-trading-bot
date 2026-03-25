from django.db import models

from apps.common.models import TimeStampedModel


class OperatorAlertType(models.TextChoices):
    APPROVAL_REQUIRED = 'approval_required', 'Approval required'
    SAFETY = 'safety', 'Safety'
    RUNTIME = 'runtime', 'Runtime'
    SYNC = 'sync', 'Sync'
    READINESS = 'readiness', 'Readiness'
    QUEUE = 'queue', 'Queue'
    PORTFOLIO = 'portfolio', 'Portfolio'
    ANOMALY = 'anomaly', 'Anomaly'


class OperatorAlertSeverity(models.TextChoices):
    INFO = 'info', 'Info'
    WARNING = 'warning', 'Warning'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'


class OperatorAlertStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'
    RESOLVED = 'RESOLVED', 'Resolved'
    SUPPRESSED = 'SUPPRESSED', 'Suppressed'


class OperatorAlertSource(models.TextChoices):
    OPERATOR_QUEUE = 'operator_queue', 'Operator queue'
    SAFETY = 'safety', 'Safety'
    RUNTIME = 'runtime', 'Runtime'
    REAL_SYNC = 'real_sync', 'Real sync'
    CONTINUOUS_DEMO = 'continuous_demo', 'Continuous demo'
    EVALUATION = 'evaluation', 'Evaluation'
    READINESS = 'readiness', 'Readiness'
    MANUAL = 'manual', 'Manual'


class OperatorDigestType(models.TextChoices):
    DAILY = 'daily', 'Daily'
    SESSION = 'session', 'Session'
    MANUAL = 'manual', 'Manual'
    CYCLE_WINDOW = 'cycle_window', 'Cycle window'


class OperatorAlert(TimeStampedModel):
    alert_type = models.CharField(max_length=24, choices=OperatorAlertType.choices)
    severity = models.CharField(max_length=12, choices=OperatorAlertSeverity.choices, default=OperatorAlertSeverity.INFO)
    status = models.CharField(max_length=16, choices=OperatorAlertStatus.choices, default=OperatorAlertStatus.OPEN)
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    source = models.CharField(max_length=24, choices=OperatorAlertSource.choices)
    related_object_type = models.CharField(max_length=64, blank=True, null=True)
    related_object_id = models.CharField(max_length=64, blank=True, null=True)
    dedupe_key = models.CharField(max_length=255, blank=True, null=True)
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-last_seen_at', '-id']
        indexes = [
            models.Index(fields=['status', '-last_seen_at']),
            models.Index(fields=['severity', '-last_seen_at']),
            models.Index(fields=['source', 'alert_type']),
            models.Index(fields=['dedupe_key']),
        ]


class OperatorDigest(TimeStampedModel):
    digest_type = models.CharField(max_length=20, choices=OperatorDigestType.choices, default=OperatorDigestType.SESSION)
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    summary = models.TextField(blank=True)
    alerts_count = models.PositiveIntegerField(default=0)
    critical_count = models.PositiveIntegerField(default=0)
    approvals_pending_count = models.PositiveIntegerField(default=0)
    safety_events_count = models.PositiveIntegerField(default=0)
    runtime_changes_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-window_end', '-id']
        indexes = [
            models.Index(fields=['digest_type', '-window_end']),
        ]

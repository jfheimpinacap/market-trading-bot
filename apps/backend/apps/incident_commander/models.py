from django.db import models

from apps.common.models import TimeStampedModel


class IncidentType(models.TextChoices):
    PROVIDER_FAILURE = 'provider_failure', 'Provider failure'
    STALE_DATA = 'stale_data', 'Stale data'
    ROLLOUT_GUARDRAIL = 'rollout_guardrail', 'Rollout guardrail'
    MISSION_CONTROL_FAILURE = 'mission_control_failure', 'Mission control failure'
    EXECUTION_ANOMALY = 'execution_anomaly', 'Execution anomaly'
    QUEUE_PRESSURE = 'queue_pressure', 'Queue pressure'
    MEMORY_INDEX_FAILURE = 'memory_index_failure', 'Memory index failure'
    LLM_UNAVAILABLE = 'llm_unavailable', 'LLM unavailable'
    RUNTIME_CONFLICT = 'runtime_conflict', 'Runtime conflict'
    SAFETY_BLOCK = 'safety_block', 'Safety block'
    ALERT_DELIVERY_FAILURE = 'alerts_delivery_failure', 'Alerts delivery failure'
    UNKNOWN = 'unknown', 'Unknown'


class IncidentSeverity(models.TextChoices):
    INFO = 'info', 'Info'
    WARNING = 'warning', 'Warning'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'


class IncidentStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    MITIGATING = 'MITIGATING', 'Mitigating'
    DEGRADED = 'DEGRADED', 'Degraded'
    RECOVERING = 'RECOVERING', 'Recovering'
    RESOLVED = 'RESOLVED', 'Resolved'
    ESCALATED = 'ESCALATED', 'Escalated'


class IncidentActionStatus(models.TextChoices):
    PLANNED = 'PLANNED', 'Planned'
    APPLIED = 'APPLIED', 'Applied'
    FAILED = 'FAILED', 'Failed'
    SKIPPED = 'SKIPPED', 'Skipped'


class RecoveryRunStatus(models.TextChoices):
    STARTED = 'STARTED', 'Started'
    SUCCESS = 'SUCCESS', 'Success'
    FAILED = 'FAILED', 'Failed'
    SKIPPED = 'SKIPPED', 'Skipped'


class DegradedSystemState(models.TextChoices):
    NORMAL = 'normal', 'Normal'
    RESEARCH_DEGRADED = 'research_degraded', 'Research degraded'
    EXECUTION_DEGRADED = 'execution_degraded', 'Execution degraded'
    ROLLOUT_DISABLED = 'rollout_disabled', 'Rollout disabled'
    AUTO_EXECUTE_DISABLED = 'auto_execute_disabled', 'Auto execute disabled'
    DEFENSIVE_ONLY = 'defensive_only', 'Defensive only'
    MISSION_CONTROL_PAUSED = 'mission_control_paused', 'Mission control paused'


class IncidentRecord(TimeStampedModel):
    incident_type = models.CharField(max_length=48, choices=IncidentType.choices, default=IncidentType.UNKNOWN)
    severity = models.CharField(max_length=12, choices=IncidentSeverity.choices, default=IncidentSeverity.WARNING)
    status = models.CharField(max_length=16, choices=IncidentStatus.choices, default=IncidentStatus.OPEN)
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    source_app = models.CharField(max_length=64)
    related_object_type = models.CharField(max_length=64, null=True, blank=True)
    related_object_id = models.CharField(max_length=64, null=True, blank=True)
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    dedupe_key = models.CharField(max_length=255, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-last_seen_at', '-id']
        indexes = [
            models.Index(fields=['status', '-last_seen_at']),
            models.Index(fields=['severity', '-last_seen_at']),
            models.Index(fields=['incident_type', '-last_seen_at']),
            models.Index(fields=['dedupe_key']),
        ]


class IncidentAction(TimeStampedModel):
    incident = models.ForeignKey(IncidentRecord, on_delete=models.CASCADE, related_name='actions')
    action_type = models.CharField(max_length=64)
    action_status = models.CharField(max_length=12, choices=IncidentActionStatus.choices, default=IncidentActionStatus.PLANNED)
    rationale = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['created_at', 'id']


class IncidentRecoveryRun(TimeStampedModel):
    incident = models.ForeignKey(IncidentRecord, on_delete=models.CASCADE, related_name='recovery_runs')
    run_status = models.CharField(max_length=12, choices=RecoveryRunStatus.choices, default=RecoveryRunStatus.STARTED)
    trigger = models.CharField(max_length=64, default='system')
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class DegradedModeState(TimeStampedModel):
    state = models.CharField(max_length=40, choices=DegradedSystemState.choices, default=DegradedSystemState.NORMAL)
    mission_control_paused = models.BooleanField(default=False)
    auto_execution_enabled = models.BooleanField(default=True)
    rollout_enabled = models.BooleanField(default=True)
    degraded_modules = models.JSONField(default=list, blank=True)
    disabled_actions = models.JSONField(default=list, blank=True)
    reasons = models.JSONField(default=list, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']

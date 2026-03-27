from django.db import models

from apps.common.models import TimeStampedModel


class ChaosExperimentSeverity(models.TextChoices):
    LOW = 'low', 'Low'
    WARNING = 'warning', 'Warning'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'


class ChaosExperimentType(models.TextChoices):
    PROVIDER_SYNC_FAILURE = 'provider_sync_failure', 'Provider sync failure'
    LLM_UNAVAILABLE = 'llm_unavailable', 'LLM unavailable'
    MISSION_CONTROL_STEP_FAILURE = 'mission_control_step_failure', 'Mission control step failure'
    ROLLOUT_GUARDRAIL_TRIGGER = 'rollout_guardrail_trigger', 'Rollout guardrail trigger'
    QUEUE_PRESSURE_SPIKE = 'queue_pressure_spike', 'Queue pressure spike'
    NOTIFICATION_DELIVERY_FAILURE = 'notification_delivery_failure', 'Notification delivery failure'
    STALE_DATA_SCENARIO = 'stale_data_scenario', 'Stale data scenario'
    EXECUTION_FILL_ANOMALY = 'execution_fill_anomaly', 'Execution fill anomaly'


class ChaosRunStatus(models.TextChoices):
    RUNNING = 'RUNNING', 'Running'
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    FAILED = 'FAILED', 'Failed'
    ABORTED = 'ABORTED', 'Aborted'


class ChaosTriggerMode(models.TextChoices):
    MANUAL = 'manual', 'Manual'
    SCHEDULED = 'scheduled', 'Scheduled'
    BENCHMARK_SUITE = 'benchmark_suite', 'Benchmark suite'


class ObservationSeverity(models.TextChoices):
    INFO = 'info', 'Info'
    WARNING = 'warning', 'Warning'
    ERROR = 'error', 'Error'


class ChaosExperiment(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=128, unique=True)
    experiment_type = models.CharField(max_length=64, choices=ChaosExperimentType.choices)
    is_enabled = models.BooleanField(default=True)
    severity = models.CharField(max_length=12, choices=ChaosExperimentSeverity.choices, default=ChaosExperimentSeverity.WARNING)
    target_module = models.CharField(max_length=64)
    description = models.CharField(max_length=255, blank=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['name', 'id']
        indexes = [
            models.Index(fields=['is_enabled', 'severity']),
            models.Index(fields=['target_module', 'is_enabled']),
        ]


class ChaosRun(TimeStampedModel):
    experiment = models.ForeignKey(ChaosExperiment, on_delete=models.CASCADE, related_name='runs')
    status = models.CharField(max_length=16, choices=ChaosRunStatus.choices, default=ChaosRunStatus.RUNNING)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    trigger_mode = models.CharField(max_length=24, choices=ChaosTriggerMode.choices, default=ChaosTriggerMode.MANUAL)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['experiment', '-created_at']),
        ]


class ChaosObservation(TimeStampedModel):
    run = models.ForeignKey(ChaosRun, on_delete=models.CASCADE, related_name='observations')
    code = models.CharField(max_length=80)
    message = models.CharField(max_length=255)
    severity = models.CharField(max_length=12, choices=ObservationSeverity.choices, default=ObservationSeverity.INFO)
    observed_at = models.DateTimeField()
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['observed_at', 'id']
        indexes = [
            models.Index(fields=['run', 'observed_at']),
            models.Index(fields=['code', 'severity']),
        ]


class ResilienceBenchmark(TimeStampedModel):
    run = models.OneToOneField(ChaosRun, on_delete=models.CASCADE, related_name='benchmark')
    experiment = models.ForeignKey(ChaosExperiment, on_delete=models.CASCADE, related_name='benchmarks')
    detection_time_seconds = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    mitigation_time_seconds = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    recovery_time_seconds = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    incidents_created = models.PositiveIntegerField(default=0)
    degraded_mode_triggered = models.BooleanField(default=False)
    rollback_triggered = models.BooleanField(default=False)
    alerts_sent = models.PositiveIntegerField(default=0)
    queue_items_created = models.PositiveIntegerField(default=0)
    recovery_success_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    resilience_score = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    metrics = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['experiment', '-created_at']),
            models.Index(fields=['resilience_score', '-created_at']),
        ]

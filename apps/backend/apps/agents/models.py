from django.db import models

from apps.common.models import TimeStampedModel


class AgentStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    RUNNING = 'RUNNING', 'Running'
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    FAILED = 'FAILED', 'Failed'
    SKIPPED = 'SKIPPED', 'Skipped'


class AgentTriggeredFrom(models.TextChoices):
    MANUAL = 'manual', 'Manual'
    AUTOMATION = 'automation', 'Automation'
    CONTINUOUS_DEMO = 'continuous_demo', 'Continuous Demo'
    REAL_OPS = 'real_ops', 'Real Ops'
    REPLAY = 'replay', 'Replay'
    EXPERIMENT = 'experiment', 'Experiment'


class AgentPipelineType(models.TextChoices):
    RESEARCH_TO_PREDICTION = 'research_to_prediction', 'Research to Prediction'
    POSTMORTEM_TO_LEARNING = 'postmortem_to_learning', 'Postmortem to Learning'
    REAL_MARKET_AGENT_CYCLE = 'real_market_agent_cycle', 'Real-market Agent Cycle'


class AgentDefinition(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    agent_type = models.CharField(max_length=50)
    is_enabled = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    input_schema_version = models.CharField(max_length=40, default='v1')
    output_schema_version = models.CharField(max_length=40, default='v1')

    class Meta:
        ordering = ['name']


class AgentPipelineRun(TimeStampedModel):
    pipeline_type = models.CharField(max_length=64, choices=AgentPipelineType.choices)
    status = models.CharField(max_length=12, choices=AgentStatus.choices, default=AgentStatus.READY)
    triggered_from = models.CharField(max_length=32, choices=AgentTriggeredFrom.choices, default=AgentTriggeredFrom.MANUAL)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    agents_run_count = models.PositiveIntegerField(default=0)
    handoffs_count = models.PositiveIntegerField(default=0)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class AgentRun(TimeStampedModel):
    agent_definition = models.ForeignKey(AgentDefinition, on_delete=models.PROTECT, related_name='runs')
    pipeline_run = models.ForeignKey(AgentPipelineRun, on_delete=models.CASCADE, related_name='agent_runs', null=True, blank=True)
    status = models.CharField(max_length=12, choices=AgentStatus.choices, default=AgentStatus.READY)
    triggered_from = models.CharField(max_length=32, choices=AgentTriggeredFrom.choices, default=AgentTriggeredFrom.MANUAL)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class AgentHandoff(TimeStampedModel):
    from_agent_run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name='handoffs')
    to_agent_definition = models.ForeignKey(AgentDefinition, on_delete=models.PROTECT, related_name='incoming_handoffs')
    pipeline_run = models.ForeignKey(AgentPipelineRun, on_delete=models.CASCADE, related_name='handoffs', null=True, blank=True)
    handoff_type = models.CharField(max_length=120)
    payload_summary = models.CharField(max_length=255, blank=True)
    payload_ref = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

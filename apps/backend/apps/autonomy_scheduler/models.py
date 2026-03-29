from django.db import models

from apps.common.models import TimeStampedModel


class CampaignAdmissionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    READY = 'READY', 'Ready'
    DEFERRED = 'DEFERRED', 'Deferred'
    BLOCKED = 'BLOCKED', 'Blocked'
    ADMITTED = 'ADMITTED', 'Admitted'
    EXPIRED = 'EXPIRED', 'Expired'


class CampaignAdmissionSourceType(models.TextChoices):
    ROADMAP_PLAN = 'roadmap_plan', 'Roadmap plan'
    SCENARIO_RUN = 'scenario_run', 'Scenario run'
    MANUAL = 'manual', 'Manual'


class ChangeWindowStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    UPCOMING = 'UPCOMING', 'Upcoming'
    CLOSED = 'CLOSED', 'Closed'
    FROZEN = 'FROZEN', 'Frozen'


class ChangeWindowType(models.TextChoices):
    NORMAL_CHANGE = 'normal_change', 'Normal change'
    CAUTIOUS_CHANGE = 'cautious_change', 'Cautious change'
    OBSERVATION_ONLY = 'observation_only', 'Observation only'
    FREEZE_WINDOW = 'freeze_window', 'Freeze window'


class AdmissionRecommendationType(models.TextChoices):
    ADMIT_CAMPAIGN = 'ADMIT_CAMPAIGN', 'Admit campaign'
    DEFER_CAMPAIGN = 'DEFER_CAMPAIGN', 'Defer campaign'
    HOLD_QUEUE = 'HOLD_QUEUE', 'Hold queue'
    WAIT_FOR_WINDOW = 'WAIT_FOR_WINDOW', 'Wait for window'
    REORDER_ADMISSION_QUEUE = 'REORDER_ADMISSION_QUEUE', 'Reorder admission queue'
    SAFE_TO_ADMIT_NEXT = 'SAFE_TO_ADMIT_NEXT', 'Safe to admit next'
    BLOCK_ADMISSION = 'BLOCK_ADMISSION', 'Block admission'
    REQUIRE_APPROVAL_TO_ADMIT = 'REQUIRE_APPROVAL_TO_ADMIT', 'Require approval to admit'


class CampaignAdmission(TimeStampedModel):
    campaign = models.OneToOneField('autonomy_campaign.AutonomyCampaign', on_delete=models.CASCADE, related_name='admission_record')
    status = models.CharField(max_length=16, choices=CampaignAdmissionStatus.choices, default=CampaignAdmissionStatus.PENDING)
    source_type = models.CharField(max_length=20, choices=CampaignAdmissionSourceType.choices, default=CampaignAdmissionSourceType.MANUAL)
    priority_score = models.PositiveIntegerField(default=0)
    readiness_score = models.PositiveIntegerField(default=0)
    blocked_reasons = models.JSONField(default=list, blank=True)
    requested_window = models.ForeignKey('autonomy_scheduler.ChangeWindow', null=True, blank=True, on_delete=models.SET_NULL, related_name='requested_admissions')
    admitted_at = models.DateTimeField(null=True, blank=True)
    deferred_until = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-priority_score', '-readiness_score', 'created_at']
        indexes = [models.Index(fields=['status', '-created_at']), models.Index(fields=['source_type', '-priority_score'])]


class ChangeWindow(TimeStampedModel):
    name = models.CharField(max_length=120)
    status = models.CharField(max_length=12, choices=ChangeWindowStatus.choices, default=ChangeWindowStatus.UPCOMING)
    window_type = models.CharField(max_length=24, choices=ChangeWindowType.choices, default=ChangeWindowType.NORMAL_CHANGE)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    max_new_admissions = models.PositiveIntegerField(default=1)
    allowed_postures = models.JSONField(default=list, blank=True)
    blocked_domains = models.JSONField(default=list, blank=True)
    rationale = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['status', 'starts_at']), models.Index(fields=['window_type', '-created_at'])]


class SchedulerRun(TimeStampedModel):
    queue_counts = models.JSONField(default=dict, blank=True)
    ready_campaigns = models.JSONField(default=list, blank=True)
    blocked_campaigns = models.JSONField(default=list, blank=True)
    deferred_campaigns = models.JSONField(default=list, blank=True)
    current_program_posture = models.CharField(max_length=20, blank=True)
    active_window = models.ForeignKey('autonomy_scheduler.ChangeWindow', null=True, blank=True, on_delete=models.SET_NULL, related_name='scheduler_runs')
    max_admissible_starts = models.PositiveIntegerField(default=0)
    recommendations_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AdmissionRecommendation(TimeStampedModel):
    scheduler_run = models.ForeignKey('autonomy_scheduler.SchedulerRun', null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    recommendation_type = models.CharField(max_length=36, choices=AdmissionRecommendationType.choices)
    target_campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='admission_recommendations')
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    impacted_domains = models.JSONField(default=list, blank=True)
    recommended_window = models.ForeignKey('autonomy_scheduler.ChangeWindow', null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

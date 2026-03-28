from django.db import models

from apps.common.models import TimeStampedModel


class AutonomyRolloutStatus(models.TextChoices):
    OBSERVING = 'OBSERVING', 'Observing'
    STABLE = 'STABLE', 'Stable'
    CAUTION = 'CAUTION', 'Caution'
    FREEZE_RECOMMENDED = 'FREEZE_RECOMMENDED', 'Freeze recommended'
    ROLLBACK_RECOMMENDED = 'ROLLBACK_RECOMMENDED', 'Rollback recommended'
    COMPLETED = 'COMPLETED', 'Completed'
    ABORTED = 'ABORTED', 'Aborted'


class AutonomyRolloutRecommendationCode(models.TextChoices):
    KEEP_STAGE = 'KEEP_STAGE', 'Keep stage'
    REQUIRE_MORE_DATA = 'REQUIRE_MORE_DATA', 'Require more data'
    FREEZE_DOMAIN = 'FREEZE_DOMAIN', 'Freeze domain'
    ROLLBACK_STAGE = 'ROLLBACK_STAGE', 'Rollback stage'
    REVIEW_MANUALLY = 'REVIEW_MANUALLY', 'Review manually'
    STABILIZE_AND_MONITOR = 'STABILIZE_AND_MONITOR', 'Stabilize and monitor'


class AutonomyRolloutRun(TimeStampedModel):
    autonomy_stage_transition = models.ForeignKey('autonomy_manager.AutonomyStageTransition', on_delete=models.CASCADE, related_name='rollout_runs')
    domain = models.ForeignKey('autonomy_manager.AutonomyDomain', on_delete=models.CASCADE, related_name='rollout_runs')
    rollout_status = models.CharField(max_length=32, choices=AutonomyRolloutStatus.choices, default=AutonomyRolloutStatus.OBSERVING)
    observation_window_days = models.PositiveIntegerField(default=14)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['rollout_status', '-created_at'])]


class AutonomyBaselineSnapshot(TimeStampedModel):
    run = models.OneToOneField(AutonomyRolloutRun, on_delete=models.CASCADE, related_name='baseline_snapshot')
    metrics = models.JSONField(default=dict, blank=True)
    counts = models.JSONField(default=dict, blank=True)


class AutonomyPostChangeSnapshot(TimeStampedModel):
    run = models.OneToOneField(AutonomyRolloutRun, on_delete=models.CASCADE, related_name='post_change_snapshot')
    metrics = models.JSONField(default=dict, blank=True)
    counts = models.JSONField(default=dict, blank=True)
    deltas = models.JSONField(default=dict, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    sample_size = models.PositiveIntegerField(default=0)


class AutonomyRolloutRecommendation(TimeStampedModel):
    run = models.ForeignKey(AutonomyRolloutRun, on_delete=models.CASCADE, related_name='recommendations')
    recommendation = models.CharField(max_length=32, choices=AutonomyRolloutRecommendationCode.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    supporting_deltas = models.JSONField(default=dict, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    cross_domain_notes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation', '-created_at'])]

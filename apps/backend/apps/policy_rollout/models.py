from django.db import models

from apps.common.models import TimeStampedModel


class PolicyRolloutStatus(models.TextChoices):
    OBSERVING = 'OBSERVING', 'Observing'
    STABLE = 'STABLE', 'Stable'
    CAUTION = 'CAUTION', 'Caution'
    ROLLBACK_RECOMMENDED = 'ROLLBACK_RECOMMENDED', 'Rollback recommended'
    COMPLETED = 'COMPLETED', 'Completed'
    ABORTED = 'ABORTED', 'Aborted'


class PolicyRolloutRecommendationCode(models.TextChoices):
    KEEP_CHANGE = 'KEEP_CHANGE', 'Keep change'
    REQUIRE_MORE_DATA = 'REQUIRE_MORE_DATA', 'Require more data'
    ROLLBACK_CHANGE = 'ROLLBACK_CHANGE', 'Rollback change'
    REVIEW_MANUALLY = 'REVIEW_MANUALLY', 'Review manually'
    STABILIZE_AND_MONITOR = 'STABILIZE_AND_MONITOR', 'Stabilize and monitor'


class PolicyRolloutRun(TimeStampedModel):
    policy_tuning_candidate = models.ForeignKey('policy_tuning.PolicyTuningCandidate', on_delete=models.CASCADE, related_name='rollout_runs')
    application_log = models.ForeignKey('policy_tuning.PolicyTuningApplicationLog', on_delete=models.CASCADE, related_name='rollout_runs')
    rollout_status = models.CharField(max_length=32, choices=PolicyRolloutStatus.choices, default=PolicyRolloutStatus.OBSERVING)
    observation_window_days = models.PositiveIntegerField(default=14)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['rollout_status', '-created_at'])]


class PolicyBaselineSnapshot(TimeStampedModel):
    run = models.OneToOneField(PolicyRolloutRun, on_delete=models.CASCADE, related_name='baseline_snapshot')
    metrics = models.JSONField(default=dict, blank=True)
    counts = models.JSONField(default=dict, blank=True)


class PolicyPostChangeSnapshot(TimeStampedModel):
    run = models.OneToOneField(PolicyRolloutRun, on_delete=models.CASCADE, related_name='post_change_snapshot')
    metrics = models.JSONField(default=dict, blank=True)
    counts = models.JSONField(default=dict, blank=True)
    deltas = models.JSONField(default=dict, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    sample_size = models.PositiveIntegerField(default=0)


class PolicyRolloutRecommendation(TimeStampedModel):
    run = models.ForeignKey(PolicyRolloutRun, on_delete=models.CASCADE, related_name='recommendations')
    recommendation = models.CharField(max_length=32, choices=PolicyRolloutRecommendationCode.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    supporting_deltas = models.JSONField(default=dict, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation', '-created_at'])]

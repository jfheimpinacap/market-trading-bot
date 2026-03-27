from django.db import models

from apps.common.models import TimeStampedModel


class StackRolloutMode(models.TextChoices):
    SHADOW_ONLY = 'SHADOW_ONLY', 'Shadow only'
    CANARY = 'CANARY', 'Canary'
    STAGED = 'STAGED', 'Staged'


class StackRolloutRunStatus(models.TextChoices):
    RUNNING = 'RUNNING', 'Running'
    PAUSED = 'PAUSED', 'Paused'
    COMPLETED = 'COMPLETED', 'Completed'
    ROLLED_BACK = 'ROLLED_BACK', 'Rolled back'
    FAILED = 'FAILED', 'Failed'


class RolloutDecisionCode(models.TextChoices):
    CONTINUE_ROLLOUT = 'CONTINUE_ROLLOUT', 'Continue rollout'
    PAUSE_ROLLOUT = 'PAUSE_ROLLOUT', 'Pause rollout'
    ROLLBACK_NOW = 'ROLLBACK_NOW', 'Rollback now'
    COMPLETE_PROMOTION = 'COMPLETE_PROMOTION', 'Complete promotion'
    EXTEND_CANARY = 'EXTEND_CANARY', 'Extend canary'


class StackRolloutPlan(TimeStampedModel):
    champion_binding = models.ForeignKey(
        'champion_challenger.StackProfileBinding',
        on_delete=models.PROTECT,
        related_name='rollout_plans_as_champion',
    )
    candidate_binding = models.ForeignKey(
        'champion_challenger.StackProfileBinding',
        on_delete=models.PROTECT,
        related_name='rollout_plans_as_candidate',
    )
    source_review_run = models.ForeignKey(
        'promotion_committee.PromotionReviewRun',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rollout_plans',
    )
    mode = models.CharField(max_length=16, choices=StackRolloutMode.choices, default=StackRolloutMode.CANARY)
    canary_percentage = models.PositiveSmallIntegerField(default=10)
    sampling_rule = models.CharField(max_length=32, default='MARKET_HASH')
    profile_scope = models.CharField(max_length=64, blank=True)
    guardrails = models.JSONField(default=dict, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class StackRolloutRun(TimeStampedModel):
    plan = models.ForeignKey(StackRolloutPlan, on_delete=models.CASCADE, related_name='runs')
    status = models.CharField(max_length=16, choices=StackRolloutRunStatus.choices, default=StackRolloutRunStatus.RUNNING)
    current_phase = models.CharField(max_length=48, default='INITIAL_CANARY')
    routed_opportunities_count = models.PositiveIntegerField(default=0)
    champion_count = models.PositiveIntegerField(default=0)
    challenger_count = models.PositiveIntegerField(default=0)
    canary_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class RolloutGuardrailEvent(TimeStampedModel):
    run = models.ForeignKey(StackRolloutRun, on_delete=models.CASCADE, related_name='guardrail_events')
    code = models.CharField(max_length=64)
    severity = models.CharField(max_length=16, default='WARNING')
    reason = models.TextField(blank=True)
    metric_value = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    threshold_value = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class RolloutDecision(TimeStampedModel):
    run = models.ForeignKey(StackRolloutRun, on_delete=models.CASCADE, related_name='decisions')
    decision = models.CharField(max_length=32, choices=RolloutDecisionCode.choices)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    recommendation_payload = models.JSONField(default=dict, blank=True)
    actor = models.CharField(max_length=64, default='rollout_manager')

    class Meta:
        ordering = ['-created_at', '-id']

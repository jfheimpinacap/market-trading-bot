from django.db import models

from apps.common.models import TimeStampedModel
from apps.postmortem_demo.models import TradeReview


class PostmortemBoardRunStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    RUNNING = 'RUNNING', 'Running'
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    FAILED = 'FAILED', 'Failed'


class PostmortemPerspectiveType(models.TextChoices):
    NARRATIVE = 'narrative', 'Narrative'
    PREDICTION = 'prediction', 'Prediction'
    RISK = 'risk', 'Risk'
    RUNTIME = 'runtime', 'Runtime'
    LEARNING = 'learning', 'Learning'


class PostmortemReviewStatus(models.TextChoices):
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    FAILED = 'FAILED', 'Failed'
    SKIPPED = 'SKIPPED', 'Skipped'


class PostmortemBoardRun(TimeStampedModel):
    related_trade_review = models.ForeignKey(TradeReview, on_delete=models.PROTECT, related_name='board_runs')
    status = models.CharField(max_length=12, choices=PostmortemBoardRunStatus.choices, default=PostmortemBoardRunStatus.READY)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    perspectives_run_count = models.PositiveIntegerField(default=0)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PostmortemAgentReview(TimeStampedModel):
    board_run = models.ForeignKey(PostmortemBoardRun, on_delete=models.CASCADE, related_name='perspective_reviews')
    perspective_type = models.CharField(max_length=24, choices=PostmortemPerspectiveType.choices)
    status = models.CharField(max_length=12, choices=PostmortemReviewStatus.choices, default=PostmortemReviewStatus.SUCCESS)
    conclusion = models.TextField(blank=True)
    key_findings = models.JSONField(default=dict, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    recommended_actions = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['board_run', 'perspective_type'], name='postmortem_board_unique_perspective_review')
        ]


class PostmortemBoardConclusion(TimeStampedModel):
    board_run = models.OneToOneField(PostmortemBoardRun, on_delete=models.CASCADE, related_name='conclusion')
    primary_failure_mode = models.CharField(max_length=64)
    secondary_failure_modes = models.JSONField(default=list, blank=True)
    lesson_learned = models.TextField()
    recommended_adjustments = models.JSONField(default=list, blank=True)
    should_update_learning_memory = models.BooleanField(default=True)
    severity = models.CharField(max_length=16, default='medium')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

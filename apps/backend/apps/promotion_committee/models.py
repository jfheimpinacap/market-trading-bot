from django.db import models

from apps.common.models import TimeStampedModel
from apps.readiness_lab.models import ReadinessStatus


class PromotionReviewRunStatus(models.TextChoices):
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'


class PromotionRecommendationCode(models.TextChoices):
    KEEP_CURRENT_CHAMPION = 'KEEP_CURRENT_CHAMPION', 'Keep current champion'
    PROMOTE_CHALLENGER = 'PROMOTE_CHALLENGER', 'Promote challenger'
    EXTEND_SHADOW_TEST = 'EXTEND_SHADOW_TEST', 'Extend shadow test'
    REVERT_TO_CONSERVATIVE_STACK = 'REVERT_TO_CONSERVATIVE_STACK', 'Revert to conservative stack'
    MANUAL_REVIEW_REQUIRED = 'MANUAL_REVIEW_REQUIRED', 'Manual review required'


class PromotionDecisionMode(models.TextChoices):
    RECOMMENDATION_ONLY = 'RECOMMENDATION_ONLY', 'Recommendation only'
    MANUAL_APPLY = 'MANUAL_APPLY', 'Manual apply'


class StackEvidenceSnapshot(TimeStampedModel):
    champion_binding = models.ForeignKey(
        'champion_challenger.StackProfileBinding', on_delete=models.PROTECT, related_name='promotion_champion_evidence'
    )
    challenger_binding = models.ForeignKey(
        'champion_challenger.StackProfileBinding',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotion_challenger_evidence',
    )
    champion_challenger_summary = models.JSONField(default=dict, blank=True)
    execution_aware_metrics = models.JSONField(default=dict, blank=True)
    readiness_summary = models.JSONField(default=dict, blank=True)
    profile_governance_context = models.JSONField(default=dict, blank=True)
    portfolio_governor_context = models.JSONField(default=dict, blank=True)
    model_governance_summary = models.JSONField(default=dict, blank=True)
    precedent_warnings = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PromotionReviewRun(TimeStampedModel):
    status = models.CharField(max_length=16, choices=PromotionReviewRunStatus.choices, default=PromotionReviewRunStatus.COMPLETED)
    decision_mode = models.CharField(
        max_length=24, choices=PromotionDecisionMode.choices, default=PromotionDecisionMode.RECOMMENDATION_ONLY
    )
    readiness_status = models.CharField(max_length=24, choices=ReadinessStatus.choices, blank=True)
    evidence_snapshot = models.ForeignKey(
        StackEvidenceSnapshot, on_delete=models.PROTECT, related_name='promotion_review_runs'
    )
    recommendation_code = models.CharField(max_length=40, choices=PromotionRecommendationCode.choices)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    blocking_constraints = models.JSONField(default=list, blank=True)
    evidence_summary = models.JSONField(default=dict, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PromotionDecisionLog(TimeStampedModel):
    review_run = models.ForeignKey(PromotionReviewRun, on_delete=models.CASCADE, related_name='decision_logs')
    event_type = models.CharField(max_length=32, default='RECOMMENDATION_ISSUED')
    actor = models.CharField(max_length=64, default='system')
    notes = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

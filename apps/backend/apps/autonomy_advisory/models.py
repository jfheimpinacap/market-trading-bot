from django.db import models

from apps.common.models import TimeStampedModel


class AdvisoryArtifactType(models.TextChoices):
    MEMORY_PRECEDENT_NOTE = 'MEMORY_PRECEDENT_NOTE', 'Memory precedent note'
    ROADMAP_GOVERNANCE_NOTE = 'ROADMAP_GOVERNANCE_NOTE', 'Roadmap governance note'
    SCENARIO_CAUTION_NOTE = 'SCENARIO_CAUTION_NOTE', 'Scenario caution note'
    PROGRAM_POLICY_NOTE = 'PROGRAM_POLICY_NOTE', 'Program policy note'
    MANAGER_REVIEW_NOTE = 'MANAGER_REVIEW_NOTE', 'Manager review note'


class AdvisoryArtifactStatus(models.TextChoices):
    PENDING_REVIEW = 'PENDING_REVIEW', 'Pending review'
    READY = 'READY', 'Ready'
    EMITTED = 'EMITTED', 'Emitted'
    BLOCKED = 'BLOCKED', 'Blocked'
    DUPLICATE_SKIPPED = 'DUPLICATE_SKIPPED', 'Duplicate skipped'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'


class AdvisoryTargetScope(models.TextChoices):
    MEMORY = 'memory', 'Memory'
    ROADMAP = 'roadmap', 'Roadmap'
    SCENARIO = 'scenario', 'Scenario'
    PROGRAM = 'program', 'Program'
    MANAGER = 'manager', 'Manager'
    OPERATOR_REVIEW = 'operator_review', 'Operator review'


class AdvisoryRecommendationType(models.TextChoices):
    EMIT_MEMORY_PRECEDENT_NOTE = 'EMIT_MEMORY_PRECEDENT_NOTE', 'Emit memory precedent note'
    EMIT_ROADMAP_GOVERNANCE_NOTE = 'EMIT_ROADMAP_GOVERNANCE_NOTE', 'Emit roadmap governance note'
    EMIT_SCENARIO_CAUTION_NOTE = 'EMIT_SCENARIO_CAUTION_NOTE', 'Emit scenario caution note'
    EMIT_PROGRAM_POLICY_NOTE = 'EMIT_PROGRAM_POLICY_NOTE', 'Emit program policy note'
    EMIT_MANAGER_REVIEW_NOTE = 'EMIT_MANAGER_REVIEW_NOTE', 'Emit manager review note'
    SKIP_DUPLICATE_ADVISORY = 'SKIP_DUPLICATE_ADVISORY', 'Skip duplicate advisory'
    REQUIRE_MANUAL_ADVISORY_REVIEW = 'REQUIRE_MANUAL_ADVISORY_REVIEW', 'Require manual advisory review'
    REORDER_ADVISORY_PRIORITY = 'REORDER_ADVISORY_PRIORITY', 'Reorder advisory priority'


class AdvisoryRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    emitted_count = models.PositiveIntegerField(default=0)
    duplicate_skipped_count = models.PositiveIntegerField(default=0)
    memory_note_count = models.PositiveIntegerField(default=0)
    roadmap_note_count = models.PositiveIntegerField(default=0)
    scenario_note_count = models.PositiveIntegerField(default=0)
    program_note_count = models.PositiveIntegerField(default=0)
    manager_note_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AdvisoryArtifact(TimeStampedModel):
    advisory_run = models.ForeignKey(AdvisoryRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='artifacts')
    insight = models.ForeignKey('autonomy_insights.CampaignInsight', on_delete=models.PROTECT, related_name='advisory_artifacts')
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='advisory_artifacts')
    artifact_type = models.CharField(max_length=40, choices=AdvisoryArtifactType.choices)
    artifact_status = models.CharField(max_length=24, choices=AdvisoryArtifactStatus.choices, default=AdvisoryArtifactStatus.PENDING_REVIEW)
    target_scope = models.CharField(max_length=24, choices=AdvisoryTargetScope.choices)
    summary = models.CharField(max_length=255)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    emitted_by = models.CharField(max_length=120, blank=True)
    emitted_at = models.DateTimeField(null=True, blank=True)
    linked_memory_document = models.ForeignKey('memory_retrieval.MemoryDocument', null=True, blank=True, on_delete=models.SET_NULL, related_name='advisory_artifacts')
    linked_feedback_artifact = models.CharField(max_length=128, blank=True)
    linked_program_note = models.CharField(max_length=128, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['insight', 'artifact_type']),
            models.Index(fields=['artifact_status', '-created_at']),
            models.Index(fields=['target_scope', '-created_at']),
        ]


class AdvisoryRecommendation(TimeStampedModel):
    advisory_run = models.ForeignKey(AdvisoryRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    campaign_insight = models.ForeignKey('autonomy_insights.CampaignInsight', null=True, blank=True, on_delete=models.SET_NULL, related_name='advisory_recommendations')
    target_campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='advisory_recommendations')
    recommendation_type = models.CharField(max_length=48, choices=AdvisoryRecommendationType.choices)
    artifact_type = models.CharField(max_length=40, choices=AdvisoryArtifactType.choices, blank=True)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

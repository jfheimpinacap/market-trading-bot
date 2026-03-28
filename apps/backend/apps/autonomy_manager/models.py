from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class AutonomyStage(models.TextChoices):
    MANUAL = 'MANUAL', 'Manual'
    ASSISTED = 'ASSISTED', 'Assisted'
    SUPERVISED_AUTOPILOT = 'SUPERVISED_AUTOPILOT', 'Supervised autopilot'
    FROZEN = 'FROZEN', 'Frozen'
    ROLLBACK_RECOMMENDED = 'ROLLBACK_RECOMMENDED', 'Rollback recommended'


class AutonomyDomainStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    OBSERVING = 'OBSERVING', 'Observing'
    DEGRADED = 'DEGRADED', 'Degraded'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomyRecommendationCode(models.TextChoices):
    PROMOTE_TO_ASSISTED = 'PROMOTE_TO_ASSISTED', 'Promote to assisted'
    PROMOTE_TO_SUPERVISED_AUTOPILOT = 'PROMOTE_TO_SUPERVISED_AUTOPILOT', 'Promote to supervised autopilot'
    KEEP_CURRENT_STAGE = 'KEEP_CURRENT_STAGE', 'Keep current stage'
    DOWNGRADE_TO_MANUAL = 'DOWNGRADE_TO_MANUAL', 'Downgrade to manual'
    FREEZE_DOMAIN = 'FREEZE_DOMAIN', 'Freeze domain'
    REQUIRE_MORE_DATA = 'REQUIRE_MORE_DATA', 'Require more data'
    ROLLBACK_STAGE = 'ROLLBACK_STAGE', 'Rollback stage'


class AutonomyTransitionStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending approval'
    READY_TO_APPLY = 'READY_TO_APPLY', 'Ready to apply'
    APPLIED = 'APPLIED', 'Applied'
    ROLLED_BACK = 'ROLLED_BACK', 'Rolled back'


class AutonomyDomain(TimeStampedModel):
    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    owner_app = models.CharField(max_length=80, blank=True)
    action_types = models.JSONField(default=list, blank=True)
    source_apps = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['slug']


class AutonomyEnvelope(TimeStampedModel):
    domain = models.OneToOneField(AutonomyDomain, on_delete=models.CASCADE, related_name='envelope')
    max_auto_actions_per_cycle = models.PositiveIntegerField(default=1)
    approval_override_behavior = models.CharField(max_length=80, default='REQUIRE_OPERATOR_APPROVAL')
    blocked_contexts = models.JSONField(default=list, blank=True)
    degraded_mode_handling = models.CharField(max_length=80, default='DOWNGRADE_TO_MANUAL')
    certification_dependencies = models.JSONField(default=list, blank=True)
    runtime_dependencies = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)


class AutonomyStageState(TimeStampedModel):
    domain = models.OneToOneField(AutonomyDomain, on_delete=models.CASCADE, related_name='stage_state')
    current_stage = models.CharField(max_length=32, choices=AutonomyStage.choices, default=AutonomyStage.MANUAL)
    effective_stage = models.CharField(max_length=32, choices=AutonomyStage.choices, default=AutonomyStage.MANUAL)
    status = models.CharField(max_length=16, choices=AutonomyDomainStatus.choices, default=AutonomyDomainStatus.ACTIVE)
    rationale = models.CharField(max_length=255, blank=True)
    linked_policy_profiles = models.JSONField(default=list, blank=True)
    linked_action_types = models.JSONField(default=list, blank=True)
    last_changed_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['domain__slug']


class AutonomyStageRecommendation(TimeStampedModel):
    domain = models.ForeignKey(AutonomyDomain, on_delete=models.CASCADE, related_name='recommendations')
    state = models.ForeignKey(AutonomyStageState, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommendations')
    recommendation_code = models.CharField(max_length=48, choices=AutonomyRecommendationCode.choices)
    current_stage = models.CharField(max_length=32, choices=AutonomyStage.choices)
    proposed_stage = models.CharField(max_length=32, choices=AutonomyStage.choices)
    rationale = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    evidence_refs = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['domain', '-created_at']),
            models.Index(fields=['recommendation_code', '-created_at']),
        ]


class AutonomyStageTransition(TimeStampedModel):
    domain = models.ForeignKey(AutonomyDomain, on_delete=models.CASCADE, related_name='transitions')
    state = models.ForeignKey(AutonomyStageState, on_delete=models.CASCADE, related_name='transitions')
    recommendation = models.ForeignKey(AutonomyStageRecommendation, on_delete=models.SET_NULL, null=True, blank=True, related_name='transitions')
    approval_request = models.OneToOneField(
        'approval_center.ApprovalRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='autonomy_stage_transition',
    )
    status = models.CharField(max_length=24, choices=AutonomyTransitionStatus.choices, default=AutonomyTransitionStatus.DRAFT)
    previous_stage = models.CharField(max_length=32, choices=AutonomyStage.choices)
    requested_stage = models.CharField(max_length=32, choices=AutonomyStage.choices)
    applied_stage = models.CharField(max_length=32, choices=AutonomyStage.choices, blank=True)
    rationale = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    evidence_refs = models.JSONField(default=list, blank=True)
    requested_by = models.CharField(max_length=80, default='autonomy-review')
    applied_by = models.CharField(max_length=80, blank=True)
    rolled_back_by = models.CharField(max_length=80, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    rolled_back_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['domain', '-created_at']),
        ]

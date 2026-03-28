from django.db import models

from apps.common.models import TimeStampedModel


class ApprovalSourceType(models.TextChoices):
    RUNBOOK_CHECKPOINT = 'runbook_checkpoint', 'Runbook checkpoint'
    GO_LIVE_REQUEST = 'go_live_request', 'Go-live request'
    OPERATOR_QUEUE_ITEM = 'operator_queue_item', 'Operator queue item'
    ROLLOUT_DECISION = 'rollout_decision', 'Rollout decision'
    PROMOTION_REVIEW = 'promotion_review', 'Promotion review'
    OTHER = 'other', 'Other'


class ApprovalRequestStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    EXPIRED = 'EXPIRED', 'Expired'
    ESCALATED = 'ESCALATED', 'Escalated'
    CANCELLED = 'CANCELLED', 'Cancelled'


class ApprovalPriority(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class ApprovalDecisionType(models.TextChoices):
    APPROVE = 'APPROVE', 'Approve'
    REJECT = 'REJECT', 'Reject'
    EXPIRE = 'EXPIRE', 'Expire'
    ESCALATE = 'ESCALATE', 'Escalate'


class ApprovalRequest(TimeStampedModel):
    source_type = models.CharField(max_length=40, choices=ApprovalSourceType.choices)
    source_object_id = models.CharField(max_length=80)
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    priority = models.CharField(max_length=12, choices=ApprovalPriority.choices, default=ApprovalPriority.MEDIUM)
    status = models.CharField(max_length=16, choices=ApprovalRequestStatus.choices, default=ApprovalRequestStatus.PENDING)
    requested_at = models.DateTimeField()
    decided_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-requested_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['source_type', 'source_object_id'], name='approval_request_unique_source_binding'),
        ]
        indexes = [
            models.Index(fields=['status', '-requested_at']),
            models.Index(fields=['priority', '-requested_at']),
        ]


class ApprovalDecision(TimeStampedModel):
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.CASCADE, related_name='decisions')
    decision = models.CharField(max_length=16, choices=ApprovalDecisionType.choices)
    rationale = models.TextField(blank=True)
    decided_by = models.CharField(max_length=120, default='local-operator')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['approval_request', '-created_at'])]

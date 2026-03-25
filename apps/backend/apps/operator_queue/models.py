from django.db import models

from apps.common.models import TimeStampedModel
from apps.markets.models import Market
from apps.paper_trading.models import PaperTrade
from apps.proposal_engine.models import TradeProposal
from apps.semi_auto_demo.models import PendingApproval


class OperatorQueueStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    SNOOZED = 'SNOOZED', 'Snoozed'
    EXPIRED = 'EXPIRED', 'Expired'
    EXECUTED = 'EXECUTED', 'Executed'


class OperatorQueueSource(models.TextChoices):
    POLICY = 'policy', 'Policy'
    SAFETY = 'safety', 'Safety'
    ALLOCATION = 'allocation', 'Allocation'
    SEMI_AUTO = 'semi_auto', 'Semi-auto'
    CONTINUOUS_DEMO = 'continuous_demo', 'Continuous demo'
    REAL_OPS = 'real_ops', 'Real ops'


class OperatorQueueType(models.TextChoices):
    APPROVAL_REQUIRED = 'approval_required', 'Approval required'
    ESCALATION = 'escalation', 'Escalation'
    SAFETY_REVIEW = 'safety_review', 'Safety review'
    BLOCKED_REVIEW = 'blocked_review', 'Blocked review'


class OperatorQueuePriority(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'


class OperatorQueueItem(TimeStampedModel):
    status = models.CharField(max_length=16, choices=OperatorQueueStatus.choices, default=OperatorQueueStatus.PENDING)
    source = models.CharField(max_length=24, choices=OperatorQueueSource.choices, default=OperatorQueueSource.SEMI_AUTO)
    queue_type = models.CharField(max_length=24, choices=OperatorQueueType.choices, default=OperatorQueueType.APPROVAL_REQUIRED)
    related_proposal = models.ForeignKey(TradeProposal, null=True, blank=True, on_delete=models.SET_NULL, related_name='operator_queue_items')
    related_market = models.ForeignKey(Market, null=True, blank=True, on_delete=models.SET_NULL, related_name='operator_queue_items')
    related_pending_approval = models.ForeignKey(PendingApproval, null=True, blank=True, on_delete=models.SET_NULL, related_name='operator_queue_items')
    related_trade = models.ForeignKey(PaperTrade, null=True, blank=True, on_delete=models.SET_NULL, related_name='operator_queue_items')
    priority = models.CharField(max_length=16, choices=OperatorQueuePriority.choices, default=OperatorQueuePriority.MEDIUM)
    headline = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    rationale = models.TextField(blank=True)
    suggested_action = models.CharField(max_length=16, blank=True)
    suggested_quantity = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    snoozed_until = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['priority', '-created_at']),
            models.Index(fields=['source', 'queue_type']),
        ]


class OperatorDecisionType(models.TextChoices):
    APPROVE = 'APPROVE', 'Approve'
    REJECT = 'REJECT', 'Reject'
    SNOOZE = 'SNOOZE', 'Snooze'
    CANCEL = 'CANCEL', 'Cancel'
    FORCE_BLOCK = 'FORCE_BLOCK', 'Force block'


class OperatorDecisionLog(TimeStampedModel):
    queue_item = models.ForeignKey(OperatorQueueItem, on_delete=models.CASCADE, related_name='decision_logs')
    decision = models.CharField(max_length=16, choices=OperatorDecisionType.choices)
    decided_by = models.CharField(max_length=120, default='local-operator')
    decision_note = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['queue_item', '-created_at']),
            models.Index(fields=['decision', '-created_at']),
        ]

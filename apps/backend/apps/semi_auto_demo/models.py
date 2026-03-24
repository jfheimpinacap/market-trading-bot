from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.markets.models import Market
from apps.paper_trading.models import PaperAccount, PaperTrade, PaperTradeType
from apps.policy_engine.models import ApprovalDecisionType
from apps.proposal_engine.models import TradeProposal


class SemiAutoRunType(models.TextChoices):
    SCAN_AND_EXECUTE = 'scan_and_execute', 'Scan and execute'
    EXECUTE_AUTO = 'execute_auto', 'Execute auto'
    EVALUATE_ONLY = 'evaluate_only', 'Evaluate only'


class SemiAutoRunStatus(models.TextChoices):
    RUNNING = 'RUNNING', 'Running'
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    FAILED = 'FAILED', 'Failed'


class PendingApprovalStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    EXPIRED = 'EXPIRED', 'Expired'
    EXECUTED = 'EXECUTED', 'Executed'


class SemiAutoRun(TimeStampedModel):
    run_type = models.CharField(max_length=24, choices=SemiAutoRunType.choices)
    status = models.CharField(max_length=12, choices=SemiAutoRunStatus.choices, default=SemiAutoRunStatus.RUNNING)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    markets_evaluated = models.PositiveIntegerField(default=0)
    proposals_generated = models.PositiveIntegerField(default=0)
    auto_executed_count = models.PositiveIntegerField(default=0)
    approval_required_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class PendingApproval(TimeStampedModel):
    proposal = models.ForeignKey(TradeProposal, on_delete=models.PROTECT, related_name='pending_approvals')
    market = models.ForeignKey(Market, on_delete=models.PROTECT, related_name='pending_approvals')
    paper_account = models.ForeignKey(PaperAccount, on_delete=models.PROTECT, related_name='pending_approvals')
    status = models.CharField(max_length=16, choices=PendingApprovalStatus.choices, default=PendingApprovalStatus.PENDING)
    requested_action = models.CharField(max_length=8, choices=PaperTradeType.choices)
    suggested_side = models.CharField(max_length=8)
    suggested_quantity = models.DecimalField(max_digits=14, decimal_places=4)
    policy_decision = models.CharField(max_length=24, choices=ApprovalDecisionType.choices)
    summary = models.CharField(max_length=255)
    rationale = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)
    executed_trade = models.ForeignKey(PaperTrade, null=True, blank=True, on_delete=models.SET_NULL, related_name='pending_approvals')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['status', '-created_at', '-id']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['market', 'status']),
            models.Index(fields=['paper_account', 'status']),
        ]

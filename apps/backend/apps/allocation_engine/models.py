from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.proposal_engine.models import TradeProposal


class AllocationRunStatus(models.TextChoices):
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    FAILED = 'FAILED', 'Failed'
    SKIPPED = 'SKIPPED', 'Skipped'


class AllocationScopeType(models.TextChoices):
    REAL_ONLY = 'real_only', 'Real only'
    DEMO_ONLY = 'demo_only', 'Demo only'
    MIXED = 'mixed', 'Mixed'


class AllocationDecisionType(models.TextChoices):
    SELECTED = 'SELECTED', 'Selected'
    REDUCED = 'REDUCED', 'Reduced'
    SKIPPED = 'SKIPPED', 'Skipped'
    REJECTED = 'REJECTED', 'Rejected'


class AllocationRun(TimeStampedModel):
    status = models.CharField(max_length=12, choices=AllocationRunStatus.choices, default=AllocationRunStatus.SUCCESS)
    scope_type = models.CharField(max_length=16, choices=AllocationScopeType.choices, default=AllocationScopeType.MIXED)
    triggered_from = models.CharField(max_length=64, default='manual')
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    proposals_considered = models.PositiveIntegerField(default=0)
    proposals_ranked = models.PositiveIntegerField(default=0)
    proposals_selected = models.PositiveIntegerField(default=0)
    proposals_rejected = models.PositiveIntegerField(default=0)

    allocated_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    remaining_cash = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class AllocationDecision(TimeStampedModel):
    run = models.ForeignKey(AllocationRun, on_delete=models.CASCADE, related_name='decisions')
    proposal = models.ForeignKey(TradeProposal, on_delete=models.PROTECT, related_name='allocation_decisions')
    rank = models.PositiveIntegerField(default=0)
    final_allocated_quantity = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    decision = models.CharField(max_length=12, choices=AllocationDecisionType.choices)
    rationale = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['rank', 'id']
        indexes = [
            models.Index(fields=['run', 'rank']),
            models.Index(fields=['decision', '-created_at']),
        ]

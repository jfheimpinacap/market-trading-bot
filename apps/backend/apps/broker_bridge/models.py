from django.db import models

from apps.common.models import TimeStampedModel
from apps.execution_simulator.models import PaperOrder
from apps.markets.models import Market


class BrokerIntentStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    VALIDATED = 'VALIDATED', 'Validated'
    REJECTED = 'REJECTED', 'Rejected'
    DRY_RUN_READY = 'DRY_RUN_READY', 'Dry-run ready'
    DRY_RUN_EXECUTED = 'DRY_RUN_EXECUTED', 'Dry-run executed'


class BrokerValidationOutcome(models.TextChoices):
    VALID = 'VALID', 'Valid'
    INVALID = 'INVALID', 'Invalid'
    MANUAL_REVIEW = 'MANUAL_REVIEW', 'Manual review'


class BrokerDryRunResponse(models.TextChoices):
    ACCEPTED = 'accepted', 'Accepted'
    REJECTED = 'rejected', 'Rejected'
    HOLD = 'hold', 'Hold'
    NEEDS_MANUAL_REVIEW = 'needs_manual_review', 'Needs manual review'


class BrokerOrderIntent(TimeStampedModel):
    source_type = models.CharField(max_length=40, default='paper_order')
    source_id = models.CharField(max_length=64, blank=True)
    source_ref = models.CharField(max_length=128, blank=True)
    related_paper_order = models.ForeignKey(PaperOrder, null=True, blank=True, on_delete=models.SET_NULL, related_name='broker_intents')

    market = models.ForeignKey(Market, null=True, blank=True, on_delete=models.SET_NULL, related_name='broker_intents')
    market_ref = models.CharField(max_length=128, blank=True)
    symbol = models.CharField(max_length=64, blank=True)

    side = models.CharField(max_length=24)
    order_type = models.CharField(max_length=32, default='market')
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    limit_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    time_in_force = models.CharField(max_length=16, default='GTC')

    mapping_profile = models.CharField(max_length=64, default='generic_prediction_market')
    created_from = models.CharField(max_length=48, default='manual')
    status = models.CharField(max_length=24, choices=BrokerIntentStatus.choices, default=BrokerIntentStatus.DRAFT)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['source_type', 'source_id']),
            models.Index(fields=['mapping_profile', '-created_at']),
        ]


class BrokerBridgeValidation(TimeStampedModel):
    intent = models.ForeignKey(BrokerOrderIntent, on_delete=models.CASCADE, related_name='validations')
    outcome = models.CharField(max_length=24, choices=BrokerValidationOutcome.choices)
    is_valid = models.BooleanField(default=False)
    requires_manual_review = models.BooleanField(default=False)
    blocking_reasons = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    missing_fields = models.JSONField(default=list, blank=True)
    checks = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['outcome', '-created_at'])]


class BrokerDryRun(TimeStampedModel):
    intent = models.ForeignKey(BrokerOrderIntent, on_delete=models.CASCADE, related_name='dry_runs')
    validation = models.ForeignKey(BrokerBridgeValidation, null=True, blank=True, on_delete=models.SET_NULL, related_name='dry_runs')
    simulated_response = models.CharField(max_length=32, choices=BrokerDryRunResponse.choices)
    dry_run_summary = models.CharField(max_length=255, blank=True)
    simulated_payload = models.JSONField(default=dict, blank=True)
    simulated_broker_response = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['simulated_response', '-created_at'])]

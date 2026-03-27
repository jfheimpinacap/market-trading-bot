from django.db import models

from apps.common.models import TimeStampedModel


class VenueResponseStatus(models.TextChoices):
    ACCEPTED = 'ACCEPTED', 'Accepted'
    REJECTED = 'REJECTED', 'Rejected'
    HOLD = 'HOLD', 'Hold'
    REQUIRES_CONFIRMATION = 'REQUIRES_CONFIRMATION', 'Requires confirmation'
    UNSUPPORTED = 'UNSUPPORTED', 'Unsupported'
    INVALID_PAYLOAD = 'INVALID_PAYLOAD', 'Invalid payload'


class VenueParityStatus(models.TextChoices):
    PARITY_OK = 'PARITY_OK', 'Parity ok'
    PARITY_GAP = 'PARITY_GAP', 'Parity gap'


class VenueCapabilityProfile(TimeStampedModel):
    adapter_name = models.CharField(max_length=64, unique=True, default='null_sandbox')
    venue_name = models.CharField(max_length=64, default='sandbox_venue')
    supports_market_like = models.BooleanField(default=True)
    supports_limit_like = models.BooleanField(default=True)
    supports_reduce_only = models.BooleanField(default=True)
    supports_close_order = models.BooleanField(default=True)
    supports_partial_updates = models.BooleanField(default=False)
    requires_symbol_mapping = models.BooleanField(default=True)
    requires_manual_confirmation = models.BooleanField(default=False)
    paper_only_supported = models.BooleanField(default=True)
    live_supported = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['adapter_name', '-id']


class VenueOrderPayload(TimeStampedModel):
    intent = models.ForeignKey('broker_bridge.BrokerOrderIntent', on_delete=models.CASCADE, related_name='venue_payloads')
    venue_name = models.CharField(max_length=64)
    external_market_id = models.CharField(max_length=128, blank=True)
    side = models.CharField(max_length=32)
    order_type = models.CharField(max_length=32)
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    limit_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    tif = models.CharField(max_length=16, blank=True)
    reduce_only = models.BooleanField(default=False)
    close_flag = models.BooleanField(default=False)
    source_intent_id = models.PositiveIntegerField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['venue_name', '-created_at']),
            models.Index(fields=['source_intent_id', '-created_at']),
        ]


class VenueOrderResponse(TimeStampedModel):
    intent = models.ForeignKey('broker_bridge.BrokerOrderIntent', on_delete=models.CASCADE, related_name='venue_responses')
    payload = models.ForeignKey(VenueOrderPayload, null=True, blank=True, on_delete=models.SET_NULL, related_name='responses')
    external_order_id = models.CharField(max_length=128, null=True, blank=True)
    normalized_status = models.CharField(max_length=32, choices=VenueResponseStatus.choices)
    reason_codes = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['normalized_status', '-created_at'])]


class VenueParityRun(TimeStampedModel):
    intent = models.ForeignKey('broker_bridge.BrokerOrderIntent', on_delete=models.CASCADE, related_name='venue_parity_runs')
    payload = models.ForeignKey(VenueOrderPayload, null=True, blank=True, on_delete=models.SET_NULL, related_name='parity_runs')
    response = models.ForeignKey(VenueOrderResponse, null=True, blank=True, on_delete=models.SET_NULL, related_name='parity_runs')
    parity_status = models.CharField(max_length=24, choices=VenueParityStatus.choices)
    issues = models.JSONField(default=list, blank=True)
    missing_fields = models.JSONField(default=list, blank=True)
    unsupported_actions = models.JSONField(default=list, blank=True)
    readiness_score = models.PositiveSmallIntegerField(default=0)
    bridge_dry_run_id = models.PositiveIntegerField(null=True, blank=True)
    simulator_order_id = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['parity_status', '-created_at'])]

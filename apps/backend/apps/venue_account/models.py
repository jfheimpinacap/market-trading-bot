from decimal import Decimal

from django.db import models

from apps.common.models import TimeStampedModel


class VenueAccountMode(models.TextChoices):
    SANDBOX_ONLY = 'SANDBOX_ONLY', 'Sandbox only'


class VenueOrderMirrorStatus(models.TextChoices):
    NEW = 'NEW', 'New'
    OPEN = 'OPEN', 'Open'
    PARTIALLY_FILLED = 'PARTIALLY_FILLED', 'Partially filled'
    FILLED = 'FILLED', 'Filled'
    CANCELLED = 'CANCELLED', 'Cancelled'
    EXPIRED = 'EXPIRED', 'Expired'
    REJECTED = 'REJECTED', 'Rejected'


class VenuePositionMirrorStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    CLOSED = 'CLOSED', 'Closed'


class VenueReconciliationStatus(models.TextChoices):
    PARITY_OK = 'PARITY_OK', 'Parity ok'
    PARITY_GAP = 'PARITY_GAP', 'Parity gap'


class VenueIssueType(models.TextChoices):
    MISSING_EXTERNAL_ORDER = 'missing_external_order', 'Missing external order'
    MISSING_INTERNAL_ORDER = 'missing_internal_order', 'Missing internal order'
    FILL_QUANTITY_MISMATCH = 'fill_quantity_mismatch', 'Fill quantity mismatch'
    STATUS_MISMATCH = 'status_mismatch', 'Status mismatch'
    BALANCE_DRIFT = 'balance_drift', 'Balance drift'
    POSITION_QUANTITY_MISMATCH = 'position_quantity_mismatch', 'Position quantity mismatch'
    UNSUPPORTED_MAPPING = 'unsupported_mapping', 'Unsupported mapping'
    STALE_SNAPSHOT = 'stale_snapshot', 'Stale snapshot'


class VenueIssueSeverity(models.TextChoices):
    INFO = 'INFO', 'Info'
    WARNING = 'WARNING', 'Warning'
    HIGH = 'HIGH', 'High'


class VenueAccountSnapshot(TimeStampedModel):
    venue_name = models.CharField(max_length=64, default='sandbox_venue')
    account_reference = models.CharField(max_length=128, default='sandbox-account-001')
    account_mode = models.CharField(max_length=24, choices=VenueAccountMode.choices, default=VenueAccountMode.SANDBOX_ONLY)
    equity = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    cash_available = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    reserved_cash = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    open_positions_count = models.PositiveIntegerField(default=0)
    open_orders_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class VenueBalanceSnapshot(TimeStampedModel):
    account_snapshot = models.ForeignKey(VenueAccountSnapshot, on_delete=models.CASCADE, related_name='balances')
    currency = models.CharField(max_length=8, default='USD')
    available = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    reserved = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class VenuePositionSnapshot(TimeStampedModel):
    external_instrument_ref = models.CharField(max_length=128)
    side = models.CharField(max_length=24)
    quantity = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal('0.0000'))
    avg_entry_price = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0.0000'))
    unrealized_pnl = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    source_internal_position = models.ForeignKey(
        'paper_trading.PaperPosition',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='venue_position_snapshots',
    )
    status = models.CharField(max_length=12, choices=VenuePositionMirrorStatus.choices, default=VenuePositionMirrorStatus.OPEN)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['status', '-updated_at']),
            models.Index(fields=['external_instrument_ref', 'side']),
        ]


class VenueOrderSnapshot(TimeStampedModel):
    source_intent = models.ForeignKey('broker_bridge.BrokerOrderIntent', null=True, blank=True, on_delete=models.SET_NULL, related_name='venue_order_snapshots')
    source_paper_order = models.ForeignKey('execution_simulator.PaperOrder', null=True, blank=True, on_delete=models.SET_NULL, related_name='venue_order_snapshots')
    source_intent_ref_id = models.PositiveIntegerField(null=True, blank=True)
    external_order_id = models.CharField(max_length=128, unique=True)
    instrument_ref = models.CharField(max_length=128)
    side = models.CharField(max_length=24)
    quantity = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal('0.0000'))
    filled_quantity = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal('0.0000'))
    remaining_quantity = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal('0.0000'))
    status = models.CharField(max_length=20, choices=VenueOrderMirrorStatus.choices, default=VenueOrderMirrorStatus.NEW)
    last_response_status = models.CharField(max_length=32, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['status', '-updated_at']),
            models.Index(fields=['source_intent_ref_id', '-updated_at']),
        ]


class VenueReconciliationRun(TimeStampedModel):
    status = models.CharField(max_length=24, choices=VenueReconciliationStatus.choices, default=VenueReconciliationStatus.PARITY_OK)
    positions_compared = models.PositiveIntegerField(default=0)
    orders_compared = models.PositiveIntegerField(default=0)
    balances_compared = models.PositiveIntegerField(default=0)
    mismatches_count = models.PositiveIntegerField(default=0)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class VenueReconciliationIssue(TimeStampedModel):
    reconciliation_run = models.ForeignKey(VenueReconciliationRun, on_delete=models.CASCADE, related_name='issues')
    issue_type = models.CharField(max_length=40, choices=VenueIssueType.choices)
    severity = models.CharField(max_length=12, choices=VenueIssueSeverity.choices, default=VenueIssueSeverity.WARNING)
    reason = models.CharField(max_length=255)
    source_refs = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['issue_type', '-created_at'])]

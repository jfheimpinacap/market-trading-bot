from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.markets.models import Market
from apps.paper_trading.models import PaperAccount


class PaperOrderSide(models.TextChoices):
    BUY_YES = 'BUY_YES', 'Buy Yes'
    BUY_NO = 'BUY_NO', 'Buy No'
    SELL_YES = 'SELL_YES', 'Sell Yes'
    SELL_NO = 'SELL_NO', 'Sell No'
    REDUCE = 'REDUCE', 'Reduce'
    CLOSE = 'CLOSE', 'Close'


class PaperOrderType(models.TextChoices):
    MARKET_LIKE = 'market_like', 'Market-like'
    LIMIT_LIKE = 'limit_like', 'Limit-like'
    CLOSE_ORDER = 'close_order', 'Close order'


class PaperOrderStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    PARTIALLY_FILLED = 'PARTIALLY_FILLED', 'Partially filled'
    FILLED = 'FILLED', 'Filled'
    CANCELLED = 'CANCELLED', 'Cancelled'
    EXPIRED = 'EXPIRED', 'Expired'
    REJECTED = 'REJECTED', 'Rejected'


class PaperOrderCreatedFrom(models.TextChoices):
    OPPORTUNITY_SUPERVISOR = 'opportunity_supervisor', 'Opportunity supervisor'
    POSITION_MANAGER = 'position_manager', 'Position manager'
    OPERATOR_QUEUE = 'operator_queue', 'Operator queue'
    MANUAL = 'manual', 'Manual'


class PaperExecutionAttemptStatus(models.TextChoices):
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    NO_FILL = 'NO_FILL', 'No fill'
    CANCELLED = 'CANCELLED', 'Cancelled'
    EXPIRED = 'EXPIRED', 'Expired'
    FAILED = 'FAILED', 'Failed'


class PaperFillType(models.TextChoices):
    FULL = 'full', 'Full'
    PARTIAL = 'partial', 'Partial'


class ExecutionPolicyProfile(models.TextChoices):
    OPTIMISTIC = 'optimistic_paper', 'Optimistic paper'
    BALANCED = 'balanced_paper', 'Balanced paper'
    CONSERVATIVE = 'conservative_paper', 'Conservative paper'


class PaperOrder(TimeStampedModel):
    paper_account = models.ForeignKey(PaperAccount, on_delete=models.CASCADE, related_name='paper_orders')
    market = models.ForeignKey(Market, on_delete=models.PROTECT, related_name='paper_orders')
    side = models.CharField(max_length=16, choices=PaperOrderSide.choices)
    requested_quantity = models.DecimalField(max_digits=14, decimal_places=4)
    remaining_quantity = models.DecimalField(max_digits=14, decimal_places=4)
    order_type = models.CharField(max_length=16, choices=PaperOrderType.choices, default=PaperOrderType.MARKET_LIKE)
    requested_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    created_from = models.CharField(max_length=32, choices=PaperOrderCreatedFrom.choices, default=PaperOrderCreatedFrom.MANUAL)
    status = models.CharField(max_length=20, choices=PaperOrderStatus.choices, default=PaperOrderStatus.OPEN)
    effective_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    wait_cycles = models.PositiveIntegerField(default=0)
    max_wait_cycles = models.PositiveIntegerField(default=3)
    cancel_after_n_cycles = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['paper_account', 'status']),
            models.Index(fields=['market', 'status']),
            models.Index(fields=['created_from', 'status']),
        ]

    def __str__(self) -> str:
        return f'Order#{self.id} {self.side} {self.remaining_quantity}/{self.requested_quantity}'


class PaperExecutionAttempt(TimeStampedModel):
    paper_order = models.ForeignKey(PaperOrder, on_delete=models.CASCADE, related_name='attempts')
    attempt_status = models.CharField(max_length=16, choices=PaperExecutionAttemptStatus.choices)
    market_price_snapshot = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    effective_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    filled_quantity = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal('0.0000'))
    slippage_bps = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rationale = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['paper_order', 'attempt_status']),
        ]


class PaperFill(TimeStampedModel):
    paper_order = models.ForeignKey(PaperOrder, on_delete=models.CASCADE, related_name='fills')
    fill_quantity = models.DecimalField(max_digits=14, decimal_places=4)
    fill_price = models.DecimalField(max_digits=12, decimal_places=4)
    fill_type = models.CharField(max_length=12, choices=PaperFillType.choices)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['paper_order', 'created_at']),
        ]


class PaperOrderLifecycleRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    orders_reviewed = models.PositiveIntegerField(default=0)
    orders_open = models.PositiveIntegerField(default=0)
    orders_filled = models.PositiveIntegerField(default=0)
    orders_partial = models.PositiveIntegerField(default=0)
    orders_cancelled = models.PositiveIntegerField(default=0)
    orders_expired = models.PositiveIntegerField(default=0)
    no_fill_attempts = models.PositiveIntegerField(default=0)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']

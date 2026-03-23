from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.common.models import TimeStampedModel
from apps.markets.models import Market


class PaperCurrency(models.TextChoices):
    USD = 'USD', 'US Dollar'


class PaperPositionSide(models.TextChoices):
    YES = 'YES', 'Yes'
    NO = 'NO', 'No'


class PaperTradeType(models.TextChoices):
    BUY = 'BUY', 'Buy'
    SELL = 'SELL', 'Sell'


class PaperTradeStatus(models.TextChoices):
    EXECUTED = 'EXECUTED', 'Executed'
    CANCELLED = 'CANCELLED', 'Cancelled'
    REJECTED = 'REJECTED', 'Rejected'


class PaperPositionStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    CLOSED = 'CLOSED', 'Closed'


class PaperAccount(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=64, unique=True)
    currency = models.CharField(max_length=8, choices=PaperCurrency.choices, default=PaperCurrency.USD)
    initial_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('10000.00'))
    cash_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('10000.00'))
    reserved_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    equity = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('10000.00'))
    realized_pnl = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    unrealized_pnl = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total_pnl = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['name', 'id']
        indexes = [
            models.Index(fields=['is_active', 'slug']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class PaperPosition(TimeStampedModel):
    account = models.ForeignKey(PaperAccount, on_delete=models.CASCADE, related_name='positions')
    market = models.ForeignKey(Market, on_delete=models.PROTECT, related_name='paper_positions')
    side = models.CharField(max_length=8, choices=PaperPositionSide.choices)
    quantity = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal('0.0000'))
    average_entry_price = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0.0000'))
    current_mark_price = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0.0000'))
    cost_basis = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    market_value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    realized_pnl = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    unrealized_pnl = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=8, choices=PaperPositionStatus.choices, default=PaperPositionStatus.OPEN)
    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    last_marked_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['account', 'market', 'side'], name='paper_position_account_market_side_uniq'),
        ]
        indexes = [
            models.Index(fields=['account', 'status']),
            models.Index(fields=['market', 'status']),
            models.Index(fields=['account', 'side']),
        ]

    def __str__(self) -> str:
        return f'{self.account.slug}: {self.market.title} [{self.side}]'


class PaperTrade(TimeStampedModel):
    account = models.ForeignKey(PaperAccount, on_delete=models.CASCADE, related_name='trades')
    market = models.ForeignKey(Market, on_delete=models.PROTECT, related_name='paper_trades')
    position = models.ForeignKey(
        PaperPosition,
        on_delete=models.SET_NULL,
        related_name='trades',
        null=True,
        blank=True,
    )
    trade_type = models.CharField(max_length=8, choices=PaperTradeType.choices)
    side = models.CharField(max_length=8, choices=PaperPositionSide.choices)
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
    )
    price = models.DecimalField(max_digits=12, decimal_places=4)
    gross_amount = models.DecimalField(max_digits=14, decimal_places=2)
    fees = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=12, choices=PaperTradeStatus.choices, default=PaperTradeStatus.EXECUTED)
    executed_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-executed_at', '-id']
        indexes = [
            models.Index(fields=['account', 'status']),
            models.Index(fields=['market', 'executed_at']),
            models.Index(fields=['trade_type', 'side']),
        ]

    def __str__(self) -> str:
        return f'{self.trade_type} {self.side} {self.quantity} @ {self.price}'


class PaperPortfolioSnapshot(TimeStampedModel):
    account = models.ForeignKey(PaperAccount, on_delete=models.CASCADE, related_name='snapshots')
    captured_at = models.DateTimeField(default=timezone.now)
    cash_balance = models.DecimalField(max_digits=14, decimal_places=2)
    equity = models.DecimalField(max_digits=14, decimal_places=2)
    realized_pnl = models.DecimalField(max_digits=14, decimal_places=2)
    unrealized_pnl = models.DecimalField(max_digits=14, decimal_places=2)
    total_pnl = models.DecimalField(max_digits=14, decimal_places=2)
    open_positions_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-captured_at', '-id']
        indexes = [
            models.Index(fields=['account', '-captured_at']),
        ]

    def __str__(self) -> str:
        return f'{self.account.slug} snapshot @ {self.captured_at.isoformat()}'

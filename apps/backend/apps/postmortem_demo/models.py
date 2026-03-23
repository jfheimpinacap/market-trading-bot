from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.markets.models import Market
from apps.paper_trading.models import PaperAccount, PaperTrade


class TradeReviewStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    REVIEWED = 'REVIEWED', 'Reviewed'
    STALE = 'STALE', 'Stale'


class TradeReviewOutcome(models.TextChoices):
    FAVORABLE = 'FAVORABLE', 'Favorable'
    NEUTRAL = 'NEUTRAL', 'Neutral'
    UNFAVORABLE = 'UNFAVORABLE', 'Unfavorable'


class TradeReview(TimeStampedModel):
    paper_trade = models.OneToOneField(PaperTrade, on_delete=models.CASCADE, related_name='review')
    paper_account = models.ForeignKey(PaperAccount, on_delete=models.CASCADE, related_name='trade_reviews')
    market = models.ForeignKey(Market, on_delete=models.PROTECT, related_name='trade_reviews')
    review_status = models.CharField(max_length=12, choices=TradeReviewStatus.choices, default=TradeReviewStatus.REVIEWED)
    outcome = models.CharField(max_length=16, choices=TradeReviewOutcome.choices)
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
    )
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('1.00'))],
    )
    summary = models.CharField(max_length=255)
    rationale = models.TextField(blank=True)
    lesson = models.TextField(blank=True)
    recommendation = models.TextField(blank=True)
    entry_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    current_market_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    price_delta = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    pnl_estimate = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    market_probability_at_trade = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    market_probability_now = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    signals_context = models.JSONField(default=list, blank=True)
    risk_decision_at_trade = models.CharField(max_length=12, blank=True)
    reviewed_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-reviewed_at', '-id']
        indexes = [
            models.Index(fields=['paper_account', 'review_status']),
            models.Index(fields=['market', 'outcome']),
            models.Index(fields=['outcome', '-reviewed_at']),
        ]

    def __str__(self) -> str:
        return f'Review #{self.pk} trade #{self.paper_trade_id} => {self.outcome}'

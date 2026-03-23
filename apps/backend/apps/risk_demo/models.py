from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel
from apps.markets.models import Market
from apps.paper_trading.models import PaperAccount, PaperPositionSide, PaperTradeType


class TradeRiskDecision(models.TextChoices):
    APPROVE = 'APPROVE', 'Approve'
    CAUTION = 'CAUTION', 'Caution'
    BLOCK = 'BLOCK', 'Block'


class TradeRiskAssessment(TimeStampedModel):
    market = models.ForeignKey(Market, on_delete=models.PROTECT, related_name='risk_assessments')
    paper_account = models.ForeignKey(
        PaperAccount,
        on_delete=models.SET_NULL,
        related_name='risk_assessments',
        null=True,
        blank=True,
    )
    side = models.CharField(max_length=8, choices=PaperPositionSide.choices)
    trade_type = models.CharField(max_length=8, choices=PaperTradeType.choices)
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    requested_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    current_market_probability = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    current_yes_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    current_no_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    decision = models.CharField(max_length=12, choices=TradeRiskDecision.choices)
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
    warnings = models.JSONField(default=list, blank=True)
    suggested_quantity = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    is_actionable = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['decision', '-created_at']),
            models.Index(fields=['market', '-created_at']),
            models.Index(fields=['paper_account', '-created_at']),
        ]

    def __str__(self) -> str:
        return f'{self.market.title} [{self.trade_type} {self.side}] => {self.decision}'

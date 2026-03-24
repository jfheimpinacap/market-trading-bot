from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel
from apps.markets.models import Market
from apps.paper_trading.models import PaperAccount, PaperPositionSide
from apps.policy_engine.models import ApprovalDecisionType
from apps.risk_demo.models import TradeRiskDecision


class ProposalStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    STALE = 'STALE', 'Stale'
    SUPERSEDED = 'SUPERSEDED', 'Superseded'
    REJECTED = 'REJECTED', 'Rejected'
    EXECUTED = 'EXECUTED', 'Executed'


class ProposalDirection(models.TextChoices):
    BUY_YES = 'BUY_YES', 'Buy YES'
    BUY_NO = 'BUY_NO', 'Buy NO'
    HOLD = 'HOLD', 'Hold'
    AVOID = 'AVOID', 'Avoid'

class ProposalTradeType(models.TextChoices):
    BUY = 'BUY', 'Buy'
    SELL = 'SELL', 'Sell'
    HOLD = 'HOLD', 'Hold'


class TradeProposal(TimeStampedModel):
    market = models.ForeignKey(Market, on_delete=models.PROTECT, related_name='trade_proposals')
    paper_account = models.ForeignKey(
        PaperAccount,
        on_delete=models.SET_NULL,
        related_name='trade_proposals',
        null=True,
        blank=True,
    )
    proposal_status = models.CharField(max_length=16, choices=ProposalStatus.choices, default=ProposalStatus.ACTIVE)
    direction = models.CharField(max_length=12, choices=ProposalDirection.choices)
    proposal_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
    )
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('1.00'))],
    )
    headline = models.CharField(max_length=255)
    thesis = models.TextField()
    rationale = models.TextField(blank=True)
    suggested_trade_type = models.CharField(max_length=8, choices=ProposalTradeType.choices)
    suggested_side = models.CharField(max_length=8, choices=PaperPositionSide.choices, null=True, blank=True)
    suggested_quantity = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    suggested_price_reference = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    risk_decision = models.CharField(max_length=12, choices=TradeRiskDecision.choices)
    policy_decision = models.CharField(max_length=24, choices=ApprovalDecisionType.choices)
    approval_required = models.BooleanField(default=False)
    is_actionable = models.BooleanField(default=False)
    recommendation = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['market', '-created_at']),
            models.Index(fields=['proposal_status', '-created_at']),
            models.Index(fields=['direction', 'is_actionable']),
            models.Index(fields=['policy_decision', 'risk_decision']),
        ]

    def __str__(self) -> str:
        return f'{self.market.title} => {self.direction} ({self.proposal_status})'

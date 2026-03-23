from django.db import models

from apps.common.models import TimeStampedModel
from apps.markets.models import Market
from apps.paper_trading.models import PaperAccount, PaperPositionSide, PaperTradeType
from apps.risk_demo.models import TradeRiskAssessment, TradeRiskDecision
from apps.signals.models import MarketSignal


class ApprovalDecisionType(models.TextChoices):
    AUTO_APPROVE = 'AUTO_APPROVE', 'Auto approve'
    APPROVAL_REQUIRED = 'APPROVAL_REQUIRED', 'Approval required'
    HARD_BLOCK = 'HARD_BLOCK', 'Hard block'


class PolicySeverity(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'


class PolicyTriggeredFrom(models.TextChoices):
    MARKET_DETAIL = 'market_detail', 'Market detail'
    AUTOMATION = 'automation', 'Automation'
    SIGNAL = 'signal', 'Signal'
    SYSTEM = 'system', 'System'


class PolicyRequestedBy(models.TextChoices):
    USER = 'user', 'User'
    AUTOMATION_DEMO = 'automation_demo', 'Automation demo'
    SYSTEM = 'system', 'System'


class ApprovalDecision(TimeStampedModel):
    market = models.ForeignKey(Market, on_delete=models.PROTECT, related_name='approval_decisions')
    paper_account = models.ForeignKey(
        PaperAccount,
        on_delete=models.SET_NULL,
        related_name='approval_decisions',
        null=True,
        blank=True,
    )
    risk_assessment = models.ForeignKey(
        TradeRiskAssessment,
        on_delete=models.SET_NULL,
        related_name='approval_decisions',
        null=True,
        blank=True,
    )
    linked_signal = models.ForeignKey(
        MarketSignal,
        on_delete=models.SET_NULL,
        related_name='approval_decisions',
        null=True,
        blank=True,
    )
    trade_type = models.CharField(max_length=8, choices=PaperTradeType.choices)
    side = models.CharField(max_length=8, choices=PaperPositionSide.choices)
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    requested_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    estimated_gross_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    requested_by = models.CharField(max_length=32, choices=PolicyRequestedBy.choices, default=PolicyRequestedBy.USER)
    triggered_from = models.CharField(max_length=32, choices=PolicyTriggeredFrom.choices, default=PolicyTriggeredFrom.MARKET_DETAIL)
    decision = models.CharField(max_length=24, choices=ApprovalDecisionType.choices)
    severity = models.CharField(max_length=12, choices=PolicySeverity.choices, default=PolicySeverity.LOW)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    summary = models.CharField(max_length=255)
    rationale = models.TextField(blank=True)
    matched_rules = models.JSONField(default=list, blank=True)
    recommendation = models.TextField(blank=True)
    risk_decision = models.CharField(max_length=12, choices=TradeRiskDecision.choices, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['decision', '-created_at']),
            models.Index(fields=['market', '-created_at']),
            models.Index(fields=['paper_account', '-created_at']),
            models.Index(fields=['triggered_from', 'requested_by']),
        ]

    def __str__(self) -> str:
        return f'{self.market.title} [{self.trade_type} {self.side}] => {self.decision}'

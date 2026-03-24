from decimal import Decimal

from django.db import models

from apps.common.models import TimeStampedModel


class SafetyStatus(models.TextChoices):
    HEALTHY = 'HEALTHY', 'Healthy'
    WARNING = 'WARNING', 'Warning'
    COOLDOWN = 'COOLDOWN', 'Cooldown'
    PAUSED = 'PAUSED', 'Paused'
    HARD_STOP = 'HARD_STOP', 'Hard stop'
    KILL_SWITCH = 'KILL_SWITCH', 'Kill switch'


class SafetyEventType(models.TextChoices):
    WARNING = 'WARNING', 'Warning'
    COOLDOWN_TRIGGERED = 'COOLDOWN_TRIGGERED', 'Cooldown triggered'
    AUTO_PAUSE_TRIGGERED = 'AUTO_PAUSE_TRIGGERED', 'Auto pause triggered'
    HARD_STOP_TRIGGERED = 'HARD_STOP_TRIGGERED', 'Hard stop triggered'
    KILL_SWITCH_TRIGGERED = 'KILL_SWITCH_TRIGGERED', 'Kill switch triggered'
    EXPOSURE_LIMIT_HIT = 'EXPOSURE_LIMIT_HIT', 'Exposure limit hit'
    DRAWDOWN_LIMIT_HIT = 'DRAWDOWN_LIMIT_HIT', 'Drawdown limit hit'
    ERROR_LIMIT_HIT = 'ERROR_LIMIT_HIT', 'Error limit hit'
    APPROVAL_ESCALATION = 'APPROVAL_ESCALATION', 'Approval escalation'


class SafetySeverity(models.TextChoices):
    INFO = 'INFO', 'Info'
    WARNING = 'WARNING', 'Warning'
    CRITICAL = 'CRITICAL', 'Critical'


class SafetyEventSource(models.TextChoices):
    CONTINUOUS_DEMO = 'continuous_demo', 'Continuous demo'
    SEMI_AUTO = 'semi_auto', 'Semi auto'
    POLICY = 'policy', 'Policy'
    PORTFOLIO = 'portfolio', 'Portfolio'
    MANUAL = 'manual', 'Manual'


class SafetyPolicyConfig(TimeStampedModel):
    name = models.CharField(max_length=64, unique=True, default='default')
    status = models.CharField(max_length=16, choices=SafetyStatus.choices, default=SafetyStatus.HEALTHY)
    status_message = models.CharField(max_length=255, blank=True)

    max_auto_trades_per_cycle = models.PositiveIntegerField(default=2)
    max_auto_trades_per_session = models.PositiveIntegerField(default=20)
    max_position_value_per_market = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('750.00'))
    max_total_open_exposure = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('3000.00'))
    max_daily_or_session_drawdown = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('800.00'))
    max_unrealized_loss_threshold = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('600.00'))
    max_consecutive_unfavorable_reviews = models.PositiveIntegerField(default=3)
    max_consecutive_failed_cycles = models.PositiveIntegerField(default=3)
    cooldown_after_block_count = models.PositiveIntegerField(default=3)
    cooldown_cycles = models.PositiveIntegerField(default=2)
    hard_stop_after_loss_threshold = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('1200.00'))
    hard_stop_after_error_count = models.PositiveIntegerField(default=5)
    require_manual_approval_above_quantity = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal('10.0000'))
    require_manual_approval_above_exposure = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('2000.00'))

    kill_switch_enabled = models.BooleanField(default=False)
    block_new_cycles_when_kill_switch = models.BooleanField(default=True)

    cooldown_until_cycle = models.PositiveIntegerField(null=True, blank=True)
    hard_stop_active = models.BooleanField(default=False)
    paused_by_safety = models.BooleanField(default=False)

    consecutive_blocked_runs = models.PositiveIntegerField(default=0)
    consecutive_failed_cycles_count = models.PositiveIntegerField(default=0)
    consecutive_unfavorable_reviews_count = models.PositiveIntegerField(default=0)
    consecutive_error_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['id']


class SafetyEvent(TimeStampedModel):
    event_type = models.CharField(max_length=40, choices=SafetyEventType.choices)
    severity = models.CharField(max_length=12, choices=SafetySeverity.choices, default=SafetySeverity.INFO)
    source = models.CharField(max_length=32, choices=SafetyEventSource.choices)
    related_session_id = models.PositiveIntegerField(null=True, blank=True)
    related_cycle_id = models.PositiveIntegerField(null=True, blank=True)
    related_market_id = models.PositiveIntegerField(null=True, blank=True)
    related_trade_id = models.PositiveIntegerField(null=True, blank=True)
    message = models.CharField(max_length=255)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['severity', '-created_at']),
            models.Index(fields=['source', '-created_at']),
        ]

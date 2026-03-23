from django.db import models


class DemoAutomationRun(models.Model):
    class ActionType(models.TextChoices):
        SIMULATE_TICK = 'simulate_tick', 'Simulate tick'
        GENERATE_SIGNALS = 'generate_signals', 'Generate signals'
        REVALUE_PORTFOLIO = 'revalue_portfolio', 'Revalue portfolio'
        GENERATE_TRADE_REVIEWS = 'generate_trade_reviews', 'Generate trade reviews'
        SYNC_DEMO_STATE = 'sync_demo_state', 'Sync demo state'
        RUN_DEMO_CYCLE = 'run_demo_cycle', 'Run demo cycle'

    class Status(models.TextChoices):
        RUNNING = 'RUNNING', 'Running'
        SUCCESS = 'SUCCESS', 'Success'
        PARTIAL = 'PARTIAL', 'Partial'
        FAILED = 'FAILED', 'Failed'

    class TriggeredFrom(models.TextChoices):
        AUTOMATION_PAGE = 'automation_page', 'Automation page'
        DASHBOARD = 'dashboard', 'Dashboard'
        SYSTEM = 'system', 'System'
        API = 'api', 'API'

    action_type = models.CharField(max_length=64, choices=ActionType.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RUNNING)
    summary = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    triggered_from = models.CharField(max_length=32, choices=TriggeredFrom.choices, default=TriggeredFrom.API)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_at', '-id']

    def __str__(self) -> str:
        return f'{self.action_type}:{self.status}'

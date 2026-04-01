from django.contrib import admin

from apps.autonomous_trader.models import (
    AutonomousTradeCandidate,
    AutonomousTradeCycleRun,
    AutonomousTradeDecision,
    AutonomousTradeExecution,
    AutonomousTradeOutcome,
    AutonomousTradeWatchRecord,
)

admin.site.register(AutonomousTradeCycleRun)
admin.site.register(AutonomousTradeCandidate)
admin.site.register(AutonomousTradeDecision)
admin.site.register(AutonomousTradeExecution)
admin.site.register(AutonomousTradeWatchRecord)
admin.site.register(AutonomousTradeOutcome)

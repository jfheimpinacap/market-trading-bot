from django.contrib import admin

from apps.risk_agent.models import PositionWatchEvent, PositionWatchRun, RiskAssessment, RiskSizingDecision

admin.site.register(RiskAssessment)
admin.site.register(RiskSizingDecision)
admin.site.register(PositionWatchRun)
admin.site.register(PositionWatchEvent)

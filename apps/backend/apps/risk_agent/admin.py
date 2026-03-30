from django.contrib import admin

from apps.risk_agent.models import (
    PositionWatchEvent,
    PositionWatchPlan,
    PositionWatchRun,
    RiskApprovalDecision,
    RiskAssessment,
    RiskRuntimeCandidate,
    RiskRuntimeRecommendation,
    RiskRuntimeRun,
    RiskSizingDecision,
    RiskSizingPlan,
)

admin.site.register(RiskAssessment)
admin.site.register(RiskSizingDecision)
admin.site.register(PositionWatchRun)
admin.site.register(PositionWatchEvent)
admin.site.register(RiskRuntimeRun)
admin.site.register(RiskRuntimeCandidate)
admin.site.register(RiskApprovalDecision)
admin.site.register(RiskSizingPlan)
admin.site.register(PositionWatchPlan)
admin.site.register(RiskRuntimeRecommendation)

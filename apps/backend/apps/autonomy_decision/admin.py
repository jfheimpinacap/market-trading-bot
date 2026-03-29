from django.contrib import admin

from apps.autonomy_decision.models import DecisionRecommendation, DecisionRun, GovernanceDecision

admin.site.register(GovernanceDecision)
admin.site.register(DecisionRun)
admin.site.register(DecisionRecommendation)

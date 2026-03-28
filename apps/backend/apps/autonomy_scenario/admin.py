from django.contrib import admin

from apps.autonomy_scenario.models import AutonomyScenarioRun, ScenarioOption, ScenarioRecommendation, ScenarioRiskEstimate

admin.site.register(AutonomyScenarioRun)
admin.site.register(ScenarioOption)
admin.site.register(ScenarioRiskEstimate)
admin.site.register(ScenarioRecommendation)

from django.contrib import admin

from apps.connector_lab.models import AdapterQualificationResult, AdapterQualificationRun, AdapterReadinessRecommendation, ConnectorFixtureProfile

admin.site.register(ConnectorFixtureProfile)
admin.site.register(AdapterQualificationRun)
admin.site.register(AdapterQualificationResult)
admin.site.register(AdapterReadinessRecommendation)

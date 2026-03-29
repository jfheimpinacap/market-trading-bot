from django.contrib import admin

from apps.autonomy_launch.models import LaunchAuthorization, LaunchReadinessSnapshot, LaunchRecommendation, LaunchRun


admin.site.register(LaunchReadinessSnapshot)
admin.site.register(LaunchAuthorization)
admin.site.register(LaunchRun)
admin.site.register(LaunchRecommendation)

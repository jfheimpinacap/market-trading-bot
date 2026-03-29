from django.contrib import admin

from apps.autonomy_backlog.models import BacklogRecommendation, BacklogRun, GovernanceBacklogItem

admin.site.register(GovernanceBacklogItem)
admin.site.register(BacklogRun)
admin.site.register(BacklogRecommendation)

from django.contrib import admin

from apps.autonomy_recovery.models import RecoveryRecommendation, RecoveryRun, RecoverySnapshot

admin.site.register(RecoverySnapshot)
admin.site.register(RecoveryRun)
admin.site.register(RecoveryRecommendation)

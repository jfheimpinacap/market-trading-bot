from django.contrib import admin

from apps.runtime_governor.models import (
    GlobalOperatingModeDecision,
    GlobalOperatingModeRecommendation,
    GlobalOperatingModeSwitchRecord,
    GlobalRuntimePostureRun,
    GlobalRuntimePostureSnapshot,
    RuntimeModeProfile,
    RuntimeModeState,
    RuntimeTransitionLog,
)

admin.site.register(RuntimeModeProfile)
admin.site.register(RuntimeModeState)
admin.site.register(RuntimeTransitionLog)
admin.site.register(GlobalRuntimePostureRun)
admin.site.register(GlobalRuntimePostureSnapshot)
admin.site.register(GlobalOperatingModeDecision)
admin.site.register(GlobalOperatingModeSwitchRecord)
admin.site.register(GlobalOperatingModeRecommendation)

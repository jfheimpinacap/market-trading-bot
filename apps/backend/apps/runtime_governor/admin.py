from django.contrib import admin

from apps.runtime_governor.models import RuntimeModeProfile, RuntimeModeState, RuntimeTransitionLog

admin.site.register(RuntimeModeProfile)
admin.site.register(RuntimeModeState)
admin.site.register(RuntimeTransitionLog)

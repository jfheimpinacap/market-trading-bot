from django.contrib import admin

from apps.execution_simulator.models import PaperExecutionAttempt, PaperFill, PaperOrder, PaperOrderLifecycleRun

admin.site.register(PaperOrder)
admin.site.register(PaperExecutionAttempt)
admin.site.register(PaperFill)
admin.site.register(PaperOrderLifecycleRun)

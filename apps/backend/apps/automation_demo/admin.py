from django.contrib import admin

from apps.automation_demo.models import DemoAutomationRun


@admin.register(DemoAutomationRun)
class DemoAutomationRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'action_type', 'status', 'triggered_from', 'started_at', 'finished_at')
    list_filter = ('action_type', 'status', 'triggered_from')
    search_fields = ('summary',)
    ordering = ('-started_at', '-id')

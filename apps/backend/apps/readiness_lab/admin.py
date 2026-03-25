from django.contrib import admin

from apps.readiness_lab.models import ReadinessAssessmentRun, ReadinessProfile


@admin.register(ReadinessProfile)
class ReadinessProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'profile_type', 'is_active', 'updated_at')
    list_filter = ('profile_type', 'is_active')
    search_fields = ('name', 'slug')


@admin.register(ReadinessAssessmentRun)
class ReadinessAssessmentRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'readiness_profile', 'status', 'gates_passed_count', 'gates_failed_count', 'warnings_count', 'created_at')
    list_filter = ('status', 'readiness_profile')
    search_fields = ('summary', 'rationale')

from django.contrib import admin

from apps.profile_manager.models import ManagedProfileBinding, ProfileDecision, ProfileGovernanceRun


@admin.register(ManagedProfileBinding)
class ManagedProfileBindingAdmin(admin.ModelAdmin):
    list_display = ('module_key', 'operating_mode', 'profile_slug', 'is_active', 'updated_at')
    list_filter = ('module_key', 'operating_mode', 'is_active')
    search_fields = ('profile_slug', 'profile_label')


@admin.register(ProfileGovernanceRun)
class ProfileGovernanceRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'regime', 'runtime_mode', 'readiness_status', 'safety_status', 'started_at')
    list_filter = ('status', 'regime', 'runtime_mode', 'readiness_status', 'safety_status')
    search_fields = ('summary', 'triggered_by')


@admin.register(ProfileDecision)
class ProfileDecisionAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'decision_mode', 'target_mission_control_profile', 'target_portfolio_governor_profile', 'is_applied', 'created_at')
    list_filter = ('decision_mode', 'is_applied')
    search_fields = ('rationale',)

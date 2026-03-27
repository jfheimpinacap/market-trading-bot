from django.contrib import admin

from apps.automation_policy.models import AutomationActionLog, AutomationDecision, AutomationPolicyProfile, AutomationPolicyRule


@admin.register(AutomationPolicyProfile)
class AutomationPolicyProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'is_active', 'is_default', 'recommendation_mode', 'allow_runbook_auto_advance', 'updated_at')
    list_filter = ('is_active', 'is_default', 'recommendation_mode', 'allow_runbook_auto_advance')
    search_fields = ('slug', 'name')


@admin.register(AutomationPolicyRule)
class AutomationPolicyRuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'profile', 'action_type', 'source_context_type', 'trust_tier', 'updated_at')
    list_filter = ('trust_tier', 'profile')
    search_fields = ('action_type', 'source_context_type', 'rationale')


@admin.register(AutomationDecision)
class AutomationDecisionAdmin(admin.ModelAdmin):
    list_display = ('id', 'action_type', 'effective_trust_tier', 'outcome', 'created_at')
    list_filter = ('outcome', 'trust_tier', 'effective_trust_tier')
    search_fields = ('action_type', 'source_context_type')


@admin.register(AutomationActionLog)
class AutomationActionLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'action_name', 'execution_status', 'created_at')
    list_filter = ('execution_status',)
    search_fields = ('action_name', 'result_summary')

from django.contrib import admin

from apps.policy_tuning.models import PolicyChangeSet, PolicyTuningApplicationLog, PolicyTuningCandidate, PolicyTuningReview


@admin.register(PolicyTuningCandidate)
class PolicyTuningCandidateAdmin(admin.ModelAdmin):
    list_display = ('id', 'action_type', 'status', 'current_trust_tier', 'proposed_trust_tier', 'created_at')
    list_filter = ('status', 'action_type')
    search_fields = ('action_type', 'rationale')


admin.site.register(PolicyChangeSet)
admin.site.register(PolicyTuningReview)
admin.site.register(PolicyTuningApplicationLog)

from django.contrib import admin

from apps.autonomy_intake.models import IntakeRecommendation, IntakeRun, PlanningProposal


@admin.register(PlanningProposal)
class PlanningProposalAdmin(admin.ModelAdmin):
    list_display = ('id', 'backlog_item', 'proposal_type', 'proposal_status', 'target_scope', 'priority_level', 'emitted_at')
    list_filter = ('proposal_type', 'proposal_status', 'target_scope', 'priority_level')
    search_fields = ('summary', 'rationale', 'linked_target_artifact', 'emitted_by')


@admin.register(IntakeRun)
class IntakeRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'candidate_count', 'ready_count', 'blocked_count', 'emitted_count', 'duplicate_skipped_count', 'created_at')


@admin.register(IntakeRecommendation)
class IntakeRecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recommendation_type', 'backlog_item', 'proposal_type', 'confidence', 'created_at')
    list_filter = ('recommendation_type', 'proposal_type')

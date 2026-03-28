from django.contrib import admin

from apps.approval_center.models import ApprovalDecision, ApprovalRequest


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'source_type', 'source_object_id', 'status', 'priority', 'requested_at', 'decided_at')
    list_filter = ('source_type', 'status', 'priority')
    search_fields = ('title', 'summary', 'source_object_id')


@admin.register(ApprovalDecision)
class ApprovalDecisionAdmin(admin.ModelAdmin):
    list_display = ('id', 'approval_request', 'decision', 'decided_by', 'created_at')
    list_filter = ('decision',)
    search_fields = ('approval_request__title', 'rationale', 'decided_by')

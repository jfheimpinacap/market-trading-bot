from django.contrib import admin

from apps.policy_engine.models import ApprovalDecision


@admin.register(ApprovalDecision)
class ApprovalDecisionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created_at',
        'decision',
        'severity',
        'market',
        'paper_account',
        'trade_type',
        'side',
        'quantity',
        'triggered_from',
        'requested_by',
        'risk_decision',
        'short_summary',
    )
    list_filter = ('decision', 'severity', 'triggered_from', 'requested_by', 'risk_decision', 'market', 'paper_account')
    search_fields = ('market__title', 'market__slug', 'paper_account__name', 'paper_account__slug', 'summary', 'rationale', 'recommendation')
    ordering = ('-created_at', '-id')
    readonly_fields = (
        'market',
        'paper_account',
        'risk_assessment',
        'linked_signal',
        'trade_type',
        'side',
        'quantity',
        'requested_price',
        'estimated_gross_amount',
        'requested_by',
        'triggered_from',
        'decision',
        'severity',
        'confidence',
        'summary',
        'rationale',
        'matched_rules',
        'recommendation',
        'risk_decision',
        'metadata',
        'created_at',
        'updated_at',
    )

    @admin.display(description='Summary')
    def short_summary(self, obj):
        return obj.summary[:96]

from django.contrib import admin

from apps.risk_demo.models import TradeRiskAssessment


@admin.register(TradeRiskAssessment)
class TradeRiskAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created_at',
        'market',
        'paper_account',
        'trade_type',
        'side',
        'quantity',
        'decision',
        'score',
        'confidence',
        'is_actionable',
        'short_summary',
    )
    list_filter = ('decision', 'trade_type', 'side', 'is_actionable', 'market', 'paper_account')
    search_fields = ('market__title', 'market__slug', 'paper_account__name', 'paper_account__slug', 'summary', 'rationale')
    ordering = ('-created_at', '-id')
    readonly_fields = (
        'market',
        'paper_account',
        'trade_type',
        'side',
        'quantity',
        'requested_price',
        'current_market_probability',
        'current_yes_price',
        'current_no_price',
        'decision',
        'score',
        'confidence',
        'summary',
        'rationale',
        'warnings',
        'suggested_quantity',
        'is_actionable',
        'metadata',
        'created_at',
        'updated_at',
    )

    def short_summary(self, obj):
        return obj.summary[:80]

    short_summary.short_description = 'Summary'

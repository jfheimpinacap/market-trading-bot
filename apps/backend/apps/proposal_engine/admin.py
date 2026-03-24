from django.contrib import admin

from apps.proposal_engine.models import TradeProposal


@admin.register(TradeProposal)
class TradeProposalAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created_at',
        'market',
        'direction',
        'proposal_status',
        'suggested_trade_type',
        'suggested_side',
        'suggested_quantity',
        'risk_decision',
        'policy_decision',
        'approval_required',
        'is_actionable',
        'short_headline',
    )
    list_filter = ('direction', 'is_actionable', 'policy_decision', 'risk_decision', 'market', 'proposal_status')
    search_fields = ('market__title', 'market__slug', 'headline', 'thesis', 'recommendation')
    ordering = ('-created_at', '-id')
    readonly_fields = (
        'market',
        'paper_account',
        'proposal_status',
        'direction',
        'proposal_score',
        'confidence',
        'headline',
        'thesis',
        'rationale',
        'suggested_trade_type',
        'suggested_side',
        'suggested_quantity',
        'suggested_price_reference',
        'risk_decision',
        'policy_decision',
        'approval_required',
        'is_actionable',
        'recommendation',
        'expires_at',
        'metadata',
        'created_at',
        'updated_at',
    )

    @admin.display(description='Headline')
    def short_headline(self, obj):
        return obj.headline[:96]

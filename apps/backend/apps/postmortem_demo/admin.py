from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.postmortem_demo.models import TradeReview


@admin.register(TradeReview)
class TradeReviewAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'reviewed_at',
        'outcome',
        'review_status',
        'paper_account',
        'market_link',
        'trade_link',
        'score',
        'confidence',
        'risk_decision_at_trade',
        'short_summary',
        'short_lesson',
    )
    search_fields = (
        'paper_trade__id',
        'paper_account__name',
        'paper_account__slug',
        'market__title',
        'market__slug',
        'summary',
        'lesson',
        'recommendation',
    )
    list_filter = ('outcome', 'review_status', 'paper_account', 'market__provider', 'risk_decision_at_trade')
    ordering = ('-reviewed_at', '-id')
    autocomplete_fields = ('paper_trade', 'paper_account', 'market')
    readonly_fields = (
        'paper_trade',
        'paper_account',
        'market',
        'review_status',
        'outcome',
        'score',
        'confidence',
        'summary',
        'rationale',
        'lesson',
        'recommendation',
        'entry_price',
        'current_market_price',
        'price_delta',
        'pnl_estimate',
        'market_probability_at_trade',
        'market_probability_now',
        'signals_context',
        'risk_decision_at_trade',
        'reviewed_at',
        'metadata',
        'created_at',
        'updated_at',
    )

    @admin.display(description='Market')
    def market_link(self, obj):
        url = reverse('admin:markets_market_change', args=[obj.market_id])
        return format_html('<a href="{}">{}</a>', url, obj.market.title)

    @admin.display(description='Trade')
    def trade_link(self, obj):
        url = reverse('admin:paper_trading_papertrade_change', args=[obj.paper_trade_id])
        return format_html('<a href="{}">Trade #{}</a>', url, obj.paper_trade_id)

    @admin.display(description='Summary')
    def short_summary(self, obj):
        return obj.summary[:96]

    @admin.display(description='Lesson')
    def short_lesson(self, obj):
        return obj.lesson[:96]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('paper_trade', 'paper_account', 'market', 'market__provider')

from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from apps.paper_trading.models import (
    PaperAccount,
    PaperPortfolioSnapshot,
    PaperPosition,
    PaperPositionStatus,
    PaperTrade,
)


class PaperTradeInline(admin.TabularInline):
    model = PaperTrade
    extra = 0
    fields = ('executed_at', 'market', 'trade_type', 'side', 'quantity', 'price', 'gross_amount', 'status')
    readonly_fields = fields
    show_change_link = True
    can_delete = False
    ordering = ('-executed_at', '-id')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PaperAccount)
class PaperAccountAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
        'currency',
        'cash_balance',
        'equity',
        'realized_pnl',
        'unrealized_pnl',
        'open_positions_count',
        'is_active',
        'updated_at',
    )
    search_fields = ('name', 'slug', 'notes')
    list_filter = ('is_active', 'currency')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'equity', 'realized_pnl', 'unrealized_pnl', 'total_pnl')
    prepopulated_fields = {'slug': ('name',)}
    inlines = (PaperTradeInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(open_positions_total=Count('positions'))

    @admin.display(ordering='open_positions_total', description='Positions')
    def open_positions_count(self, obj):
        return obj.positions.filter(status=PaperPositionStatus.OPEN, quantity__gt=0).count()


@admin.register(PaperPosition)
class PaperPositionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'account',
        'market_link',
        'market_source_type',
        'side',
        'status',
        'quantity',
        'average_entry_price',
        'current_mark_price',
        'market_value',
        'unrealized_pnl',
        'updated_at',
    )
    search_fields = ('account__name', 'market__title', 'market__slug')
    list_filter = ('status', 'side', 'account', 'market__provider')
    ordering = ('-updated_at', '-id')
    autocomplete_fields = ('account', 'market')
    readonly_fields = ('created_at', 'updated_at', 'opened_at', 'closed_at', 'last_marked_at')

    @admin.display(description='Market')
    def market_link(self, obj):
        url = reverse('admin:markets_market_change', args=[obj.market_id])
        return format_html('<a href="{}">{}</a>', url, obj.market.title)

    @admin.display(description='Market source')
    def market_source_type(self, obj):
        return obj.market.source_type

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('account', 'market', 'market__provider')


@admin.register(PaperTrade)
class PaperTradeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'executed_at',
        'account',
        'market_link',
        'market_source_type',
        'trade_type',
        'side',
        'quantity',
        'price',
        'gross_amount',
        'status',
    )
    search_fields = ('account__name', 'market__title', 'notes')
    list_filter = ('trade_type', 'side', 'status', 'account', 'market__provider')
    ordering = ('-executed_at', '-id')
    autocomplete_fields = ('account', 'market', 'position')
    readonly_fields = ('created_at', 'updated_at', 'executed_at')

    @admin.display(description='Market')
    def market_link(self, obj):
        url = reverse('admin:markets_market_change', args=[obj.market_id])
        return format_html('<a href="{}">{}</a>', url, obj.market.title)

    @admin.display(description='Market source')
    def market_source_type(self, obj):
        return obj.market.source_type

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('account', 'market', 'position', 'market__provider')


@admin.register(PaperPortfolioSnapshot)
class PaperPortfolioSnapshotAdmin(admin.ModelAdmin):
    list_display = ('captured_at', 'account', 'cash_balance', 'equity', 'realized_pnl', 'unrealized_pnl', 'total_pnl', 'open_positions_count')
    search_fields = ('account__name', 'account__slug')
    list_filter = ('account', 'captured_at')
    ordering = ('-captured_at', '-id')
    autocomplete_fields = ('account',)
    readonly_fields = ('created_at', 'updated_at', 'captured_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('account')

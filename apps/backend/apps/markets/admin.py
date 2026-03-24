from django.contrib import admin
from django.db.models import Count, Max
from django.urls import reverse
from django.utils.html import format_html

from .models import Event, Market, MarketRule, MarketSnapshot, Provider


class MarketRuleInline(admin.TabularInline):
    model = MarketRule
    extra = 0
    fields = ('source_type', 'rule_text', 'resolution_criteria', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    show_change_link = True


class RecentMarketSnapshotInline(admin.TabularInline):
    model = MarketSnapshot
    extra = 0
    fields = ('captured_at', 'market_probability', 'last_price', 'liquidity', 'volume_24h')
    readonly_fields = fields
    can_delete = False
    show_change_link = True
    ordering = ('-captured_at',)
    max_num = 5

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'event_count', 'market_count', 'base_url', 'updated_at')
    search_fields = ('name', 'slug', 'description')
    list_filter = ('is_active',)
    ordering = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            event_total=Count('events', distinct=True),
            market_total=Count('markets', distinct=True),
        )

    @admin.display(ordering='event_total', description='Events')
    def event_count(self, obj):
        return obj.event_total

    @admin.display(ordering='market_total', description='Markets')
    def market_count(self, obj):
        return obj.market_total


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'provider',
        'source_type',
        'status',
        'category',
        'market_count',
        'open_time',
        'close_time',
        'updated_at',
    )
    search_fields = ('title', 'slug', 'provider_event_id', 'category', 'description')
    list_filter = ('provider', 'source_type', 'status', 'category')
    ordering = ('provider__name', 'title')
    autocomplete_fields = ('provider',)
    readonly_fields = ('created_at', 'updated_at', 'slug')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('provider').annotate(
            market_total=Count('markets', distinct=True),
        )

    @admin.display(ordering='market_total', description='Markets')
    def market_count(self, obj):
        return obj.market_total


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'provider',
        'source_type',
        'event_link',
        'status_badge',
        'market_type',
        'is_active',
        'current_market_probability',
        'liquidity',
        'snapshot_count',
        'latest_snapshot_at',
        'last_simulation_tick',
        'close_time',
    )
    search_fields = ('title', 'slug', 'ticker', 'provider_market_id', 'category', 'resolution_source')
    list_filter = ('provider', 'source_type', 'status', 'market_type', 'outcome_type', 'is_active', 'category')
    ordering = ('provider__name', 'title')
    autocomplete_fields = ('provider', 'event')
    readonly_fields = (
        'created_at',
        'updated_at',
        'slug',
        'snapshot_count',
        'latest_snapshot_at',
        'provider_market_id',
    )
    inlines = (MarketRuleInline, RecentMarketSnapshotInline)
    actions = ('mark_selected_active', 'mark_selected_inactive')

    fieldsets = (
        ('Catalog', {'fields': ('provider', 'event', 'provider_market_id', 'ticker', 'title', 'slug', 'category', 'source_type')}),
        ('Trading state', {
            'fields': (
                'status', 'is_active', 'market_type', 'outcome_type', 'current_market_probability',
                'current_yes_price', 'current_no_price', 'liquidity', 'volume_24h', 'volume_total', 'spread_bps'
            )
        }),
        ('Timing', {'fields': ('open_time', 'close_time', 'resolution_time', 'latest_snapshot_at', 'snapshot_count')}),
        ('Resolution', {'fields': ('resolution_source', 'short_rules', 'url', 'metadata')}),
        ('Audit', {'fields': ('created_at', 'updated_at')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('provider', 'event').annotate(
            snapshot_total=Count('snapshots', distinct=True),
            latest_snapshot_value=Max('snapshots__captured_at'),
        )

    @admin.action(description='Mark selected markets as active')
    def mark_selected_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} market(s) marked as active.')

    @admin.action(description='Mark selected markets as inactive')
    def mark_selected_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} market(s) marked as inactive.')

    @admin.display(ordering='event__title', description='Event')
    def event_link(self, obj):
        if not obj.event_id:
            return '—'
        url = reverse('admin:markets_event_change', args=[obj.event_id])
        return format_html('<a href="{}">{}</a>', url, obj.event.title)

    @admin.display(ordering='status', description='Status')
    def status_badge(self, obj):
        color = '#15803d' if obj.is_active else '#6b7280'
        if obj.status in {'resolved', 'closed', 'cancelled', 'archived'}:
            color = '#1d4ed8' if obj.status == 'resolved' else '#6b7280'
        if obj.status == 'paused':
            color = '#b45309'
        return format_html('<strong style="color: {}">{}</strong>', color, obj.get_status_display())

    @admin.display(ordering='snapshot_total', description='Snapshots')
    def snapshot_count(self, obj):
        return obj.snapshot_total

    @admin.display(ordering='latest_snapshot_value', description='Latest snapshot')
    def latest_snapshot_at(self, obj):
        return obj.latest_snapshot_value or '—'

    @admin.display(description='Last simulation tick')
    def last_simulation_tick(self, obj):
        simulation = (obj.metadata or {}).get('simulation', {})
        return simulation.get('last_tick_at', '—')


@admin.register(MarketSnapshot)
class MarketSnapshotAdmin(admin.ModelAdmin):
    list_display = ('market', 'provider_name', 'captured_at', 'market_probability', 'last_price', 'liquidity', 'volume_24h')
    search_fields = ('market__title', 'market__slug', 'market__provider_market_id')
    list_filter = ('market__provider', 'captured_at')
    ordering = ('-captured_at',)
    autocomplete_fields = ('market',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'captured_at'

    @admin.display(ordering='market__provider__name', description='Provider')
    def provider_name(self, obj):
        return obj.market.provider.name

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('market', 'market__provider')


@admin.register(MarketRule)
class MarketRuleAdmin(admin.ModelAdmin):
    list_display = ('market', 'provider_name', 'source_type', 'created_at', 'updated_at')
    search_fields = ('market__title', 'rule_text', 'resolution_criteria')
    list_filter = ('source_type', 'market__provider')
    ordering = ('market__title', 'source_type', '-created_at')
    autocomplete_fields = ('market',)
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(ordering='market__provider__name', description='Provider')
    def provider_name(self, obj):
        return obj.market.provider.name

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('market', 'market__provider')

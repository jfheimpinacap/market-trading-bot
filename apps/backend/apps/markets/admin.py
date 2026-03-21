from django.contrib import admin

from .models import Event, Market, MarketRule, MarketSnapshot, Provider


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'base_url', 'updated_at')
    search_fields = ('name', 'slug', 'description')
    list_filter = ('is_active',)
    ordering = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'provider', 'status', 'category', 'open_time', 'close_time', 'updated_at')
    search_fields = ('title', 'slug', 'provider_event_id', 'category', 'description')
    list_filter = ('provider', 'status', 'category')
    ordering = ('provider__name', 'title')
    autocomplete_fields = ('provider',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'provider',
        'event',
        'status',
        'market_type',
        'outcome_type',
        'is_active',
        'close_time',
        'updated_at',
    )
    search_fields = ('title', 'slug', 'ticker', 'provider_market_id', 'category', 'resolution_source')
    list_filter = ('provider', 'status', 'market_type', 'outcome_type', 'is_active', 'category')
    ordering = ('provider__name', 'title')
    autocomplete_fields = ('provider', 'event')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(MarketSnapshot)
class MarketSnapshotAdmin(admin.ModelAdmin):
    list_display = ('market', 'captured_at', 'market_probability', 'last_price', 'liquidity', 'volume_24h')
    search_fields = ('market__title', 'market__slug', 'market__provider_market_id')
    list_filter = ('market__provider', 'captured_at')
    ordering = ('-captured_at',)
    autocomplete_fields = ('market',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'captured_at'


@admin.register(MarketRule)
class MarketRuleAdmin(admin.ModelAdmin):
    list_display = ('market', 'source_type', 'created_at', 'updated_at')
    search_fields = ('market__title', 'rule_text', 'resolution_criteria')
    list_filter = ('source_type', 'market__provider')
    ordering = ('market__title', 'source_type', '-created_at')
    autocomplete_fields = ('market',)
    readonly_fields = ('created_at', 'updated_at')

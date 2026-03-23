from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from apps.signals.models import MarketSignal, MockAgent, SignalRun


@admin.register(MockAgent)
class MockAgentAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'role_type', 'is_active', 'signal_count', 'updated_at')
    search_fields = ('name', 'slug', 'description', 'notes')
    list_filter = ('role_type', 'is_active')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(signal_total=Count('signals'))

    @admin.display(ordering='signal_total', description='Signals')
    def signal_count(self, obj):
        return obj.signal_total


@admin.register(SignalRun)
class SignalRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'run_type', 'status', 'markets_evaluated', 'signals_created', 'started_at', 'finished_at')
    search_fields = ('run_type', 'status', 'notes')
    list_filter = ('run_type', 'status', 'started_at')
    ordering = ('-started_at', '-id')
    readonly_fields = ('created_at', 'updated_at', 'started_at', 'finished_at')


@admin.register(MarketSignal)
class MarketSignalAdmin(admin.ModelAdmin):
    list_display = (
        'headline',
        'market_link',
        'agent',
        'signal_type',
        'status',
        'direction_badge',
        'score',
        'confidence',
        'is_actionable',
        'created_at',
    )
    search_fields = ('headline', 'thesis', 'rationale', 'market__title', 'agent__name', 'agent__slug')
    list_filter = ('signal_type', 'status', 'direction', 'is_actionable', 'agent', 'market__provider')
    ordering = ('-created_at', '-score', '-confidence')
    autocomplete_fields = ('market', 'agent', 'run')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Market')
    def market_link(self, obj):
        url = reverse('admin:markets_market_change', args=[obj.market_id])
        return format_html('<a href="{}">{}</a>', url, obj.market.title)

    @admin.display(ordering='direction', description='Direction')
    def direction_badge(self, obj):
        color = '#6b7280'
        if obj.direction == 'BULLISH':
            color = '#15803d'
        elif obj.direction == 'BEARISH':
            color = '#b91c1c'
        return format_html('<strong style="color: {}">{}</strong>', color, obj.get_direction_display())

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('market', 'agent', 'run', 'market__provider')

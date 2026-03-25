from django.contrib import admin

from apps.real_data_sync.models import ProviderSyncRun


@admin.register(ProviderSyncRun)
class ProviderSyncRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'provider', 'sync_type', 'status', 'markets_seen', 'snapshots_created', 'errors_count', 'started_at')
    list_filter = ('provider', 'sync_type', 'status')
    search_fields = ('summary',)
    ordering = ('-started_at', '-id')

from django.contrib import admin

from apps.broker_bridge.models import BrokerBridgeValidation, BrokerDryRun, BrokerOrderIntent


@admin.register(BrokerOrderIntent)
class BrokerOrderIntentAdmin(admin.ModelAdmin):
    list_display = ('id', 'source_type', 'source_id', 'symbol', 'side', 'quantity', 'status', 'created_at')
    list_filter = ('status', 'mapping_profile', 'source_type')
    search_fields = ('symbol', 'source_ref', 'source_id', 'market_ref')


@admin.register(BrokerBridgeValidation)
class BrokerBridgeValidationAdmin(admin.ModelAdmin):
    list_display = ('id', 'intent', 'outcome', 'is_valid', 'requires_manual_review', 'created_at')
    list_filter = ('outcome', 'is_valid', 'requires_manual_review')


@admin.register(BrokerDryRun)
class BrokerDryRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'intent', 'simulated_response', 'created_at')
    list_filter = ('simulated_response',)

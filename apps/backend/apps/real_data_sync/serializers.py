from rest_framework import serializers

from apps.real_data_sync.models import ProviderSyncRun, ProviderSyncType


class ProviderSyncRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderSyncRun
        fields = [
            'id',
            'provider',
            'sync_type',
            'status',
            'started_at',
            'finished_at',
            'triggered_from',
            'markets_seen',
            'markets_created',
            'markets_updated',
            'snapshots_created',
            'errors_count',
            'summary',
            'details',
            'created_at',
            'updated_at',
        ]


class RealSyncRunRequestSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['kalshi', 'polymarket'])
    sync_type = serializers.ChoiceField(choices=ProviderSyncType.choices, required=False)
    active_only = serializers.BooleanField(required=False, default=False)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=500, default=100)
    market_id = serializers.CharField(required=False, allow_blank=False)
    triggered_from = serializers.CharField(required=False, default='api')


class RealSyncProviderStatusSerializer(serializers.Serializer):
    provider = serializers.CharField()
    latest_run_id = serializers.IntegerField(allow_null=True)
    latest_status = serializers.CharField(allow_null=True)
    latest_started_at = serializers.DateTimeField(allow_null=True)
    last_success_at = serializers.DateTimeField(allow_null=True)
    last_failed_at = serializers.DateTimeField(allow_null=True)
    consecutive_failures = serializers.IntegerField()
    stale = serializers.BooleanField()
    availability = serializers.CharField()
    warning = serializers.CharField(allow_blank=True)


class RealSyncStatusSerializer(serializers.Serializer):
    providers = serializers.JSONField()
    stale_after_minutes = serializers.IntegerField()


class RealSyncSummarySerializer(serializers.Serializer):
    total_runs = serializers.IntegerField()
    by_status = serializers.DictField(child=serializers.IntegerField())
    by_provider = serializers.DictField(child=serializers.IntegerField())

from rest_framework import serializers

from apps.real_market_ops.models import RealMarketOperationRun


class RealMarketOperationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealMarketOperationRun
        fields = (
            'id',
            'status',
            'triggered_from',
            'started_at',
            'finished_at',
            'providers_considered',
            'markets_considered',
            'markets_eligible',
            'proposals_generated',
            'auto_executed_count',
            'approval_required_count',
            'blocked_count',
            'skipped_stale_count',
            'skipped_degraded_provider_count',
            'skipped_no_pricing_count',
            'summary',
            'details',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class RealMarketRunRequestSerializer(serializers.Serializer):
    triggered_from = serializers.ChoiceField(choices=['continuous_demo', 'automation', 'manual'], required=False, default='manual')


class RealMarketOpsStatusSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    execution_mode = serializers.CharField()
    source_type_required = serializers.CharField()
    provider_status = serializers.JSONField()
    scope = serializers.JSONField()
    latest_run = serializers.JSONField(allow_null=True)

from rest_framework import serializers

from apps.continuous_demo.models import ContinuousDemoCycleRun, ContinuousDemoSession, LoopRuntimeControl


class ContinuousDemoSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContinuousDemoSession
        fields = (
            'id',
            'session_status',
            'started_at',
            'finished_at',
            'last_cycle_at',
            'total_cycles',
            'total_auto_executed',
            'total_pending_approvals',
            'total_blocked',
            'total_errors',
            'summary',
            'settings_snapshot',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class ContinuousDemoCycleRunSerializer(serializers.ModelSerializer):
    session_status = serializers.CharField(source='session.session_status', read_only=True)

    class Meta:
        model = ContinuousDemoCycleRun
        fields = (
            'id',
            'session',
            'session_status',
            'cycle_number',
            'status',
            'started_at',
            'finished_at',
            'actions_run',
            'markets_evaluated',
            'proposals_generated',
            'auto_executed_count',
            'approval_required_count',
            'blocked_count',
            'summary',
            'details',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class ContinuousDemoControlRequestSerializer(serializers.Serializer):
    cycle_interval_seconds = serializers.IntegerField(required=False, min_value=2, max_value=3600)
    max_cycles_per_session = serializers.IntegerField(required=False, min_value=1, max_value=5000)
    max_auto_trades_per_cycle = serializers.IntegerField(required=False, min_value=0, max_value=100)
    max_auto_trades_total_per_session = serializers.IntegerField(required=False, min_value=0, max_value=5000)
    stop_on_error = serializers.BooleanField(required=False)
    market_scope = serializers.ChoiceField(required=False, choices=['demo_only', 'real_only', 'mixed'])
    review_after_trade = serializers.BooleanField(required=False)
    revalue_after_trade = serializers.BooleanField(required=False)
    enabled = serializers.BooleanField(required=False)
    learning_rebuild_enabled = serializers.BooleanField(required=False)
    learning_rebuild_every_n_cycles = serializers.IntegerField(required=False, min_value=2, max_value=500)
    learning_rebuild_after_reviews = serializers.BooleanField(required=False)
    real_data_refresh_enabled = serializers.BooleanField(required=False)
    real_data_refresh_every_n_cycles = serializers.IntegerField(required=False, min_value=2, max_value=500)
    real_data_refresh_active_only = serializers.BooleanField(required=False)
    real_data_refresh_limit = serializers.IntegerField(required=False, min_value=1, max_value=500)


class ContinuousDemoStatusSerializer(serializers.Serializer):
    runtime = serializers.JSONField()
    active_session = serializers.JSONField(allow_null=True)
    latest_cycle = serializers.JSONField(allow_null=True)
    pending_approvals = serializers.IntegerField()


class LoopRuntimeControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoopRuntimeControl
        fields = (
            'id',
            'runtime_status',
            'enabled',
            'kill_switch',
            'stop_requested',
            'pause_requested',
            'cycle_in_progress',
            'last_heartbeat_at',
            'last_error',
            'active_session',
            'default_settings',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

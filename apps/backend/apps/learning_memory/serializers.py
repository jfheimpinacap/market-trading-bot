from rest_framework import serializers

from apps.learning_memory.models import LearningAdjustment, LearningMemoryEntry, LearningRebuildRun


class LearningMemoryEntrySerializer(serializers.ModelSerializer):
    provider_slug = serializers.CharField(source='provider.slug', read_only=True)
    market_slug = serializers.CharField(source='market.slug', read_only=True)
    signal_type = serializers.CharField(source='related_signal.signal_type', read_only=True)

    class Meta:
        model = LearningMemoryEntry
        fields = (
            'id',
            'memory_type',
            'source_type',
            'provider',
            'provider_slug',
            'market',
            'market_slug',
            'related_trade',
            'related_review',
            'related_signal',
            'signal_type',
            'outcome',
            'score_delta',
            'confidence_delta',
            'quantity_bias_delta',
            'summary',
            'rationale',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class LearningAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningAdjustment
        fields = (
            'id',
            'adjustment_type',
            'scope_type',
            'scope_key',
            'is_active',
            'magnitude',
            'reason',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class LearningSummarySerializer(serializers.Serializer):
    total_memory_entries = serializers.IntegerField()
    active_adjustments = serializers.IntegerField()
    negative_patterns_detected = serializers.IntegerField()
    conservative_bias_score = serializers.DecimalField(max_digits=7, decimal_places=4)
    entries_by_outcome = serializers.DictField(child=serializers.IntegerField())
    adjustments_by_scope = serializers.DictField(child=serializers.IntegerField())
    recent_memory = LearningMemoryEntrySerializer(many=True)
    recent_adjustments = LearningAdjustmentSerializer(many=True)


class LearningRebuildRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningRebuildRun
        fields = (
            'id',
            'status',
            'triggered_from',
            'related_session',
            'related_cycle',
            'started_at',
            'finished_at',
            'memory_entries_processed',
            'adjustments_created',
            'adjustments_updated',
            'adjustments_deactivated',
            'summary',
            'details',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class LearningRebuildRequestSerializer(serializers.Serializer):
    triggered_from = serializers.ChoiceField(
        choices=LearningRebuildRun.TriggeredFrom.choices,
        required=False,
        default=LearningRebuildRun.TriggeredFrom.MANUAL,
    )
    related_session_id = serializers.IntegerField(required=False, min_value=1)
    related_cycle_id = serializers.IntegerField(required=False, min_value=1)

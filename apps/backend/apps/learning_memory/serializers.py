from rest_framework import serializers

from apps.learning_memory.models import LearningAdjustment, LearningMemoryEntry


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

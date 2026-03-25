from rest_framework import serializers

from apps.operator_queue.models import OperatorDecisionLog, OperatorQueueItem


class OperatorDecisionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperatorDecisionLog
        fields = ('id', 'decision', 'decided_by', 'decision_note', 'metadata', 'created_at', 'updated_at')
        read_only_fields = fields


class OperatorQueueItemSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='related_market.title', read_only=True)
    market_source_type = serializers.CharField(source='related_market.source_type', read_only=True)
    is_real_data = serializers.SerializerMethodField()
    proposal_headline = serializers.CharField(source='related_proposal.headline', read_only=True)
    decision_logs = OperatorDecisionLogSerializer(many=True, read_only=True)

    class Meta:
        model = OperatorQueueItem
        fields = (
            'id',
            'status',
            'source',
            'queue_type',
            'priority',
            'headline',
            'summary',
            'rationale',
            'suggested_action',
            'suggested_quantity',
            'related_proposal',
            'proposal_headline',
            'related_market',
            'market_title',
            'market_source_type',
            'is_real_data',
            'related_pending_approval',
            'related_trade',
            'expires_at',
            'snoozed_until',
            'metadata',
            'decision_logs',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_is_real_data(self, obj: OperatorQueueItem) -> bool:
        return bool(obj.related_market and obj.related_market.source_type == 'REAL_READ_ONLY')


class OperatorQueueDecisionSerializer(serializers.Serializer):
    decision_note = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    decided_by = serializers.CharField(required=False, allow_blank=True, max_length=120, default='local-operator')


class OperatorQueueSnoozeSerializer(OperatorQueueDecisionSerializer):
    snooze_hours = serializers.IntegerField(required=False, min_value=1, max_value=168, default=6)
    snooze_until = serializers.DateTimeField(required=False)
